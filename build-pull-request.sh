#!/bin/bash
set -e

echo "------------------------------------------------------------------------"
echo "Pull request detected!"
repo_name=$(echo ${GIT_URL} | awk -F/ '{print $NF}' | cut -d. -f1)
echo "Repo:  ${repo_name}"
echo "Github target branch: ${ghprbTargetBranch}"
echo "Pull request #: ${ghprbPullId}"
echo "Ref: ${sha1}"
echo "Commit: ${ghprbActualCommit}"
echo "------------------------------------------------------------------------"
echo "Checking Jenkins job properly configured..."
if [ -n ${build_system_component} ]; then
    echo "Testing pull request against ${build_system_component} component"
else
    echo "Error: Parameter 'build_system_component' not set for Jenkins job!"
    exit 1
fi
echo "------------------------------------------------------------------------"
echo "Finding local branch for '${ghprbTargetBranch}' of '${GIT_URL}'..."
local_branch=$(grep -e "\s${repo_name}\srefs/heads/${ghprbTargetBranch}\s" \
    ~xenhg/git-subscriptions | cut -d' ' -f5 | cut -d/ -f2)
if [ -z $local_branch ]; then
    echo "Error: Local build branch not found in git-subscriptions."
    exit 1
fi
echo "Github branch '${ghprbTargetBranch}' -> local branch '${local_branch}'"
echo "------------------------------------------------------------------------"
echo "Fetching local branch from build system..."
build_hg_path=/usr/local/builds/jenkins/${BUILD_TAG}
mkdir -p ${build_hg_path}
hg clone http://hg/carbon/${local_branch}/build.hg ${build_hg_path}
echo "------------------------------------------------------------------------"
echo "Populating build.hg/myrepos with build candidiate repo..."
local_repo=${build_hg_path}/myrepos/${repo_name}
git clone file://$WORKSPACE ${local_repo}
git_exe="git --git-dir=${local_repo}/.git"
${git_exe} remote set-url origin ${GIT_URL}
${git_exe} status 2> /dev/null
echo "------------------------------------------------------------------------"
echo "Start the build..."
make --directory=${build_hg_path} manifest-latest
make --directory=${build_hg_path} ${build_system_component}-build
echo "------------------------------------------------------------------------"
echo "Pulling in the RPMs from the build system to be archived..."
rpms_dir=${WORKSPACE}/rpms
rm -rf ${rpms_dir}
mkdir ${rpms_dir}
cp ${build_hg_path}/output/api/RPMS/i686/* ${rpms_dir}
echo "------------------------------------------------------------------------"
echo "Deleting build.hg"
sudo rm -rf ${build_hg_path}
echo "------------------------------------------------------------------------"
echo "End of build script"
echo "------------------------------------------------------------------------"
