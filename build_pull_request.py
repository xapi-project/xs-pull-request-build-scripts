#!/usr/bin/python

import os
import sys
import subprocess
import shutil
import time
import glob
import ConfigParser

LOCAL_BUILD_SPACE = "/usr/local/builds/jenkins"
REQUIRED_ENV_VARS = ['ghprbTargetBranch', 'ghprbPullId', 'ghprbActualCommit',
                     'WORKSPACE', 'BUILD_TAG', 'GIT_URL', 'sha1',
                     'build_system_component']


def execute(command):
    print "execute: %s" % command
    rc = subprocess.call(command.split())
    if rc != 0:
        raise Exception("Error executing command %s: Return code = %s" %
                        (command, rc))


def print_heading(msg):
    print "-" * 80
    print msg


def assert_environment_contains_vars(var_names):
    for var in var_names:
        print "Checking environment variable '%s' exists..." % var,
        try:
            assert var in os.environ
            print "OK"
        except AssertionError:
            print "Fail"
            sys.exit(1)


def repo_name_of_git_url(git_url):
    return git_url.split('/')[-1].split('.')[0]


def org_name_of_github_url(github_url):
    return github_url.split('/')[-2]


def get_local_repos(service, org, repo, refspec):
    head = ",".join((service, org, repo, refspec))
    config = ConfigParser.RawConfigParser()
    config.read("/usr/groups/sources/hg/closed/branch-info.hg/sync-git/git-subscriptions.cfg")
    result = []
    for branch in config.sections():
        if config.has_option(branch, head):
            dest_repo = config.get(branch, head).split(',')[0].split('/')[-1]
            dest_repo_name = dest_repo.rstrip(".git")
            result.append((branch, dest_repo_name))
    return result


def cleanup_job():
    build_root = os.path.join(LOCAL_BUILD_SPACE, os.environ['BUILD_TAG'])
    print_heading("Deleting temporary build root: %s ..." % build_root)
    # Retry in case bind mounts haven't released
    for _ in range(1, 5):
        try:
            execute("sudo rm -rf %s" % build_root)
        except:
            print "Deletion failed, sleeping for 3 seconds and retrying..."
            time.sleep(3)
    if os.path.exists(build_root):
        raise Exception("Cannot delete %s after build!" % build_root)


def main():
    print_heading("Pull request detected!")
    print_heading("Checking Jenkins job properly configured...")
    assert_environment_contains_vars(REQUIRED_ENV_VARS)
    repo_name = repo_name_of_git_url(os.environ['GIT_URL'])
    org_name = org_name_of_github_url(os.environ['GIT_URL'])
    print "Repo: %s" % repo_name
    print "Github organisation: %s" % org_name
    print "Github target branch: %s" % os.environ['ghprbTargetBranch']
    print "Pull request #: %s" % os.environ['ghprbPullId']
    print "Ref: %s" % os.environ['sha1']
    print "Commit: %s" % os.environ['ghprbActualCommit']

    print_heading("Removing artifacts from previous job...")
    for rpm_dir in glob.glob(os.path.join(os.environ['WORKSPACE'], 'rpms-*')):
        shutil.rmtree(rpm_dir, True)

    print_heading("Finding local branches for Github branch '%s' of '%s'..." %
                  (os.environ['ghprbTargetBranch'], os.environ['GIT_URL']))
    remote_ref = "refs/heads/%s" % os.environ['ghprbTargetBranch']
    local_repos = get_local_repos("github", org_name, repo_name, remote_ref)
    if len(local_repos) == 0:
        print "Error: Local build branch not found in git-subscriptions."
        sys.exit(2)
    else:
        print ("Github branch '%s' -> local branches '%s'" %
               (os.environ['ghprbTargetBranch'], [r[0] for r in local_repos]))
        if len(local_repos) > 1:
            print "All local branches will be built..."

    for (local_branch, local_repo_name) in local_repos:
        print_heading("Starting build for local branch '%s'" % local_branch)
        print "Fetching local branch '%s' from build system..." % local_branch
        build_hg_path = os.path.join(LOCAL_BUILD_SPACE,
                                     os.environ['BUILD_TAG'], local_branch)
        os.makedirs(build_hg_path)
        execute("hg clone http://hg/carbon/%s/build.hg %s" %
                (local_branch, build_hg_path))

        print_heading("Injecting repo into build.hg/myrepos...")
        local_repo = os.path.join(build_hg_path, "myrepos", local_repo_name)
        execute("git clone file://%s %s" %
                (os.environ['WORKSPACE'], local_repo))
        git_exe = "git --git-dir=%s/.git" % local_repo
        execute("%s remote set-url origin %s" %
                (git_exe, os.environ['GIT_URL']))
        execute("%s status" % git_exe)

        print_heading("Start the build...")

        execute("make --directory=%s manifest-latest" % build_hg_path)
        execute("make --directory=%s %s-clone" %
                (build_hg_path, os.environ['build_system_component']))

        if os.path.exists(os.path.join(build_hg_path, "obj", "repos", "planex")):
		symlink_dest = os.path.join(build_hg_path, "obj", "repos", "planex", "mk", "rpmcache")
                os.symlink("/rpmcache", symlink_dest)
        execute("make --directory=%s %s-build" %
                (build_hg_path, os.environ['build_system_component']))

        print_heading("Extracting RPMs from '%s' build.hg for archive..." %
                      local_branch)
        rpms_dir = os.path.join(os.environ['WORKSPACE'],
                                "rpms-%s" % local_branch)
        output_rpms_dir = os.path.join(build_hg_path, "output",
                                       os.environ['build_system_component'],
                                       "RPMS")
        print "Copying RPMS dir: %s -> %s..." % (output_rpms_dir, rpms_dir),
        shutil.copytree(output_rpms_dir, rpms_dir)
        print "OK"

        print_heading("Deleting build.hg for local branch '%s'" % local_branch)
        # Retry in case bind mounts haven't released
        for _ in range(1, 5):
            try:
                time.sleep(10)
                execute("sudo rm -rf %s" % build_hg_path)
            except:
                print "Deletion failed, sleeping for 10 seconds and retrying..."
        if os.path.exists(build_hg_path):
            raise Exception("Cannot delete build.hg after build!")

    cleanup_job()

    print_heading("End of build script")
    print_heading("")

if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        print_heading("Job failed (%s), attempting cleanup..." % e)
        try:
            cleanup_job()
            sys.exit(1)
        except:
            print_heading("Warning: Cleanup failed (%s)" % e)
            sys.exit(1)
