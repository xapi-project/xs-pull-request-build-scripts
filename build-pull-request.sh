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
local_branches=$(grep -e "\s${repo_name}\srefs/heads/${ghprbTargetBranch}\s" \
    ~xenhg/git-subscriptions | cut -d' ' -f5 | cut -d/ -f2)
case $(echo local_branches | wc -w) in
0)
    echo "Error: Local build branch not found in git-subscriptions."
    exit 1
    ;;
1)
    echo "Github branch '${ghprbTargetBranch}' -> local branch ${local_branches}"
    ;;
*)
    echo "Github branch '${ghprbTargetBranch}' -> local branches ${local_branches}"
    echo "All local branches will be built..."
    ;;
esac
for local_branch in ${local_branches}; do
echo "------------------------------------------------------------------------"
echo "Starting build for local branch '${local_branch}'"
    echo "--------------------------------------------------------------------"
    echo "Fetching local branch '${local_branch}' from build system..."
    build_hg_path=/usr/local/builds/jenkins/${BUILD_TAG}/${local_branch}
    mkdir -p ${build_hg_path}
    hg clone http://hg/carbon/${local_branch}/build.hg ${build_hg_path}
    echo "--------------------------------------------------------------------"
    echo "Populating build.hg/myrepos with build candidiate repo..."
    local_repo=${build_hg_path}/myrepos/${repo_name}
    git clone file://$WORKSPACE ${local_repo}
    git_exe="git --git-dir=${local_repo}/.git"
    ${git_exe} remote set-url origin ${GIT_URL}
    ${git_exe} status 2> /dev/null
    echo "--------------------------------------------------------------------"
    echo "Start the build..."
    make --directory=${build_hg_path} manifest-latest
    make --directory=${build_hg_path} ${build_system_component}-build
    echo "--------------------------------------------------------------------"
    echo "Extracting RPMs from '${local_branch}' build.hg for archive..."
    rpms_dir=${WORKSPACE}/rpms-${local_branch}
    rm -rf ${rpms_dir}
    mkdir ${rpms_dir}
    cp ${build_hg_path}/output/${build_system_component}/RPMS/i686/* ${rpms_dir}
    echo "--------------------------------------------------------------------"
    echo "Deleting build.hg for local branch '${local_branch}'"
    sudo rm -rf ${build_hg_path}
done
echo "------------------------------------------------------------------------"
echo "End of build script"
echo "------------------------------------------------------------------------"
