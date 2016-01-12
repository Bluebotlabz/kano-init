#
# user.py
#
# Copyright (C) 2015 Kano Computing Ltd.
# License: http://www.gnu.org/licenses/gpl-2.0.txt GNU GPL v2
#

"""
    A collection of functions to manipulate users on the OS.
"""

import os
import grp
import pwd
import shutil

from kano.utils import run_cmd_log, run_cmd
from kano.logging import logger

from kano_settings.system.advanced import set_user_cookies


DEFAULT_USER_PASSWORD = "kano"
DEFAULT_USER_GROUPS = "tty,adm,dialout,cdrom,audio,users,sudo,video,games," + \
                      "plugdev,input,kanousers,i2c"


class UserError(Exception):
    pass


def user_exists(name):
    """
        A predicate to test whether an user of certain name exists.

        :param name: The name of the user.
        :type name: str

        :return: True if it exists
        :rtype: bool
    """

    try:
        user = pwd.getpwnam(name)
    except KeyError:
        return False

    return user is not None


def group_exists(name):
    """
        A predicate to test whether a group of certain name exists.

        :param name: The name of the group.
        :type name: str

        :return: True if it exists
        :rtype: bool
    """

    try:
        group = grp.getgrnam(name)
    except KeyError:
        return False

    return group.gr_name == name


def get_group_members(name):
    """
        Returns a list of all the members of the group.

        :param name: The name of the group.
        :type name: str

        :return: A list of its members.
        :rtype: list
    """

    group = grp.getgrnam(name)
    return group.gr_mem


def create_user(username):
    """
        Create and initialise an account for a new user. The user will be
        added to several default groups, including kanousers.

        This function requires root permissions to run properly.

        Will rase in case of an error.

        :param username: The name of the new user
        :type name: str
    """

    if user_exists(username):
        raise UserError("The user '{}' already exists".format(username))

    home = "/home/{}".format(username)
    home_old = '/home/' + username + '-old'

    if os.path.exists(home):
        msg = ("The home directory for the new user '{}' was there already, " +
               "moving it to {}".format(username, home_old))
        logger.warn(msg)
        shutil.move(home, home_old)

    # The umask force is used to blind the actual /home/username
    # folder from other users
    umask_override = '0077'

    cmd = "useradd -u {} -m -K UMASK={} -s /bin/bash {}".format(
        get_next_uid(),
        umask_override,
        username
    )
    _, _, rv = run_cmd_log(cmd)
    if rv != 0:
        msg = "Unable to create new user, useradd failed."
        logger.error(msg)
        raise UserError(msg)

    cmd = "echo '{}:{}' | chpasswd".format(username, DEFAULT_USER_PASSWORD)
    _, _, rv = run_cmd_log(cmd)
    if rv != 0:
        delete_user(username)
        msg = "Unable to change the new user\'s password, chpasswd failed."
        logger.error(msg)
        raise UserError(msg)

    # Make sure the kanousers group exists
    if not group_exists('kanousers'):
        _, _, rv = run_cmd_log('groupadd kanousers -f')
        if rv != 0:
            msg = 'Unable to create the kanousers group, groupadd failed.'
            raise UserError(msg)

    # Add the new user to all necessary groups
    cmd = "usermod -G '{}' {}".format(DEFAULT_USER_GROUPS, username)
    _, _, rv = run_cmd_log(cmd)

    # Apply parental control configuration
    set_user_cookies(enabled=None, username=username)


def get_next_uid():
    """
        Returns the next free user id.

        :return: Free uid.
        :rtyp: int
    """

    users = pwd.getpwall()

    uids = []
    for u in users:
        uids.append(u.pw_uid)

    i = 1001
    while i in uids:
        i += 1

    return i


def make_username_unique(username_base):
    """
        Returns an unique username derived from the base.

        It appends an increasing number to the username until one that
        doesn't exist has been found. It stops after 1,000,000 tries and
        returns None in that case.

        :param username_base: The initial part of the username.
        :type username_base: str

        :returns: An unique username.
        :rtype: str
    """

    n = 1
    username = username_base
    while user_exists(username) and n <= 1000000:
        username = "{}{}".format(username_base, n)
        n += 1

    return username


def delete_user(username):
    """
        Terminates all processes of the user in question using SIGKILL
        and removes the user.

        Requires root permissions to run properly.

        :param username: The name of the user to be deleted.
        :type name: str
    """

    # kill all process from the user
    run_cmd("killall -KILL -u {}".format(username))

    _, _, rv = run_cmd_log("userdel -r {}".format(username))
    if rv != 0:
        raise UserError("Deleting the '{}' failed.".format(username))


def delete_all_users():
    """
        Terminates all processes of the user in question using SIGKILL
        and removes the user.

        Requires root permissions to run properly.

        :param username: The name of the user to be deleted.
        :type name: str
    """

    if group_exists('kanousers'):
        for user in get_group_members('kanousers'):
            delete_user(user)
