#!/usr/bin/python

import getopt
import sys
import os

JENKINS_HOME = "/var/lib/jenkins"
TEMPLATE_CONFIG = "./config.xml.template"


def usage():
    print ("""Usage: %s
           [-h|--help]
           [-n|--name] <Repository name>
           [-p|--project-url] <Github project URL>
           [-g|--git-url] <Git URL>
           [-c | --component] <Build system component>""" %
           os.path.basename(__file__))


def new_config(template, name, project_url, git_url, component, new_path):
    with open(template, 'r') as in_file:
        contents = in_file.read()
        contents.replace("@@@GIT_NAME@@@", name)
        contents.replace("@@@PROJECT_URL@@@", project_url)
        contents.replace("@@@GIT_URL@@@", git_url)
        contents.replace("@@@BUILD_SYSTEM_COMPONENT@@@", component)
        with open(new_path, 'w') as out_file:
            out_file.write(contents)


def new_jenkins_job(name, project_url, git_url, component):
    print "Creating new Jenkins Github Pull Request Builder job for %s" % name
    print "Creating directory in jenkins...",
    os.makedirs(os.path.join(JENKINS_HOME, name))
    print "Done"
    print "Creating build config...",
    conf_path = os.path.join(JENKINS_HOME, name, "config.xml")
    new_config(TEMPLATE_CONFIG, name, project_url, git_url, component,
               conf_path)
    print "Done"


def main():
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "hn:p:g:c:",
            ["help", "name=", "project-url=", "git-url=", "component="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print str(err)
        usage()
        sys.exit(2)
    name, project_url, git_url, component = None, None, None, None
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-n", "--name"):
            name = a
        elif o in ("-p", "--project-url"):
            project_url = a
        elif o in ("-g", "--git-url"):
            git_url = a
        elif o in ("-c", "--component"):
            component = a
        else:
            assert False, "unhandled option"
    if None in (name, project_url, git_url, component):
        usage()
        sys.exit(2)
    new_jenkins_job(name, project_url, git_url, component)


if __name__ == "__main__":
    main()
