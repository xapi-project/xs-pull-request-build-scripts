#!/usr/bin/python

import re
import jenkins
import urllib2
import new_jenkins_job


def update_config_admins(config):
    new_admins = new_jenkins_job.read_admins(new_jenkins_job.ADMINS_CONFIG)
    new_config = re.sub(r"<adminlist>.*</adminlist>",
                        "<adminlist>%s</adminlist>" % new_admins,
                        config)
    return new_config


def update_jenkins_job(j, name):
    try:
        config = j.get_job_config(name)
        new_config = update_config_admins(config)
        j.reconfig_job(name, new_config)
    except jenkins.JenkinsException, e:
        print "Error updating job %s: %s." % (name, e)
        raise e


def job_is_ghprb(j, name):
    try:
        config = j.get_job_config(name)
        return ('plugin="ghprb' in config)
    except jenkins.JenkinsException:
        print "Could not get config for job %s; ignoring..." % name


def update_all_jenkins_jobs():
    try:
        print "Accessing Jenkins on localhost...",
        j = jenkins.Jenkins("http://localhost:8080")
        print "Done"
        print "Getting existing jobs...",
        jobs = [job['name'] for job in j.get_jobs()]
        print "Done"
        print "Filtering out non GithubPullRequestBuilderJobs",
        jobs = [job for job in jobs if job_is_ghprb(j, job)]
        print "Done"
        for job in jobs:
            print "Updating job %s..." % job,
            update_jenkins_job(j, job)
            print "Done"
    except urllib2.URLError, e:
        print "Error connecting to Jenkins API: %s." % e


if __name__ == "__main__":
    update_all_jenkins_jobs()
