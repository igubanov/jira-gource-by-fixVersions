import os
from subprocess import call, STDOUT


def create_commit(committer_name, committer_email, timestamp, commit_message):
    os.environ["GIT_COMMITTER_NAME"] = committer_name
    os.environ["GIT_AUTHOR_NAME"] = committer_name
    os.environ["GIT_COMMITTER_EMAIL"] = committer_email
    os.environ["GIT_AUTHOR_EMAIL"] = committer_email
    os.environ["GIT_AUTHOR_DATE"] = str(timestamp)
    os.environ["GIT_COMMITTER_DATE"] = str(timestamp)
    return call(['git', 'commit', '-m', commit_message])


def is_current_dir_git_repo():
    return call(['git', 'status'], stderr=STDOUT, stdout=open(os.devnull, 'w')) == 0


def create_repo(path: str):
    is_git_repo = is_current_dir_git_repo()
    if is_git_repo:
        print("Already a git repo")
        return False
    else:
        ret = call(['git', 'init'])
        if ret != 0:
            print("Something went wrong. Return code: {0}".format(ret))
            return False
        else:
            print("Created git repo in the directory {0}".format(path))
            return True

