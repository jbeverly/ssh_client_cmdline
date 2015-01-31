#!/usr/bin/env python
import os
import getopt
import re
import sys
import pwd
import socket

# usage: ssh [-1246AaCfgKkMNnqsTtVvXxYy] [-b bind_address] [-c cipher_spec]
#           [-D [bind_address:]port] [-e escape_char] [-F configfile]
#           [-I pkcs11] [-i identity_file]
#           [-L [bind_address:]port:host:hostport]
#           [-l login_name] [-m mac_spec] [-O ctl_cmd] [-o option] [-p port]
#           [-R [bind_address:]port:host:hostport] [-S ctl_path]
#           [-W host:port] [-w local_tun[:remote_tun]]
#           [user@]hostname [command]

###############################################################################
class SSH_CmdlineParsingException(Exception):
    """ 
    Exception baseclass for SSH_CmdlineParsing
    """
    pass

###############################################################################
class Opt(object):
    """
    type for options
    """
    flag = None
    count = 0
    values = None

    def __init__(self, ssh_optstring, flag, value=None):
        """ ssh_opstring is used to determine if the Opt being built takes an argument or not """
        self.flag = flag
        if flag.lstrip('-') + ':' in ssh_optstring:
            self.values = []

        self.add(value)
        return

    def add(self, value=None):
        """ Append a value to the list of values passed to this option """
        self.count += 1
        if self.values is not None:
            self.values.append(value)

    def argv(self):
        """ get an argv array format for this option """
        optlist = []
        for n in range(self.count):
            optlist.append(self.flag)
            if self.values is not None:
                optlist.append(self.values[n])
        return optlist

    def __str__(self):
        optstr = "'"
        for n in range(self.count):
            optstr += self.flag
            if self.values is not None:
                optstr += ' ' + self.values[n]
            optstr += ' '

        optstr = optstr.rstrip()
        optstr += "'"
        return optstr

    def __repr__(self):
        return str(self)


###############################################################################
class SSH_CmdlineParsing_InvalidArgs(SSH_CmdlineParsingException):
    pass

###############################################################################
class SSH_CmdlineParsing(object):
    """
    base classs of things that need to munge an ssh-commandline
    gets the commandline in a form we can more easily adjust
    """
    ssh_optstring = '1246AaCfgKkMNnqsTtVvXxYyb:c:D:e:F:I:i:L:l:m:O:o:p:R:S:W:w:'
    ssh_path = '/usr/bin/ssh'
    argv = None
    envp = None
    args = None
    rawopts = None
    opts = None
    _hostname = None
    _username = None

    @property
    def hostname(self):
        """ hostname as string """
        if self._hostname is None:
            self.split_hostname()
        return self._hostname

    @hostname.setter
    def hostname(self, value):
        self._hostname = str(value)

    @property
    def username(self):
        """ username as string """
        if not self._username:
            self.split_hostname()
        if not self._username:
            opt = self.opts.get('-l')
            if opt is not None:
                self._username = opt.values[-1]

        return self._username

    @username.setter
    def username(self, value):
        self._username = str(value)

    @property
    def cmdline(self):
        """ argv style version of the munged commandline """
        host_arg = ''
        if self.username:
            host_arg += self.username + '@' 
        host_arg += self.hostname

        val = sum([ x.argv() for x in self.opts.values() ],[]) + [ host_arg ] + self.args[1:]
        return val

    def __init__(self, argv, envp=os.environ):
        """
        ctor, argv should be identical to a sys.argv, envp should be identical
        to an os.environ 
        """
        self.argv = argv
        self.envp = envp
        (self.rawopts, self.args) = self.parseopts();

        self.opts = {}

        for opt in self.rawopts:
            if opt[0] in self.opts:
                self.opts[opt[0]].add(opt[1])
            else:
                self.opts[opt[0]] = Opt(self.ssh_optstring, opt[0], opt[1])

        self.update_cmdline()
        return

    def parseopts(self):
        """ parse the args we've been initialized with """
        try:
            (opts, args) = getopt.getopt(self.argv, self.ssh_optstring)
        except:
            raise SSH_CmdlineParsing_InvalidArgs(   'Usage: ' + sys.argv[0] + ' [-1246AaCfgKkMNnqsTtVvXxYy] [-b bind_address] [-c cipher_spec]\n' \
                                                    ' [-D [bind_address:]port] [-e escape_char] [-F configfile]\n' \
                                                    ' [-I pkcs11] [-i identity_file]\n' \
                                                    ' [-L [bind_address:]port:host:hostport]\n' \
                                                    ' [-l login_name] [-m mac_spec] [-O ctl_cmd] [-o option] [-p port]\n' \
                                                    ' [-R [bind_address:]port:host:hostport] [-S ctl_path]\n' \
                                                    ' [-W host:port] [-w local_tun[:remote_tun]]\n' \
                                                    ' [user@]hostname [command]\n' )

        return (opts, args)

    def split_hostname(self):
        """ 
        determine if hostname was provided as user@hostname, 
        and if so, setup hostname and username pieces
        """
        #hostre = re.compile(r'(?:(?P<username>[^@]+)@)?(?P<hostname>[a-zA-Z][a-zA-Z0-9\-\.]{2,128})')
        hostre = re.compile(r'(?:(?P<username>[^@]+)@)?(?P<hostname>[a-zA-Z0-9\-\.]{2,128})')
        hostma = hostre.match(self.args[0])
        if hostma is not None:
            if self._username is None:
                self._username = hostma.groupdict()['username']
            if self._hostname is None:
                self._hostname = hostma.groupdict()['hostname']
        else:
            raise SSH_CmdlineParsingException('cannot determine hostname')
        return

    def exec_ssh(self):
        """ 
        convenience function to replace python with ssh 
        using the self.cmdline version of argv
        """
        os.execve(self.ssh_path, [self.ssh_path] + self.cmdline, self.envp)
        return

    def update_cmdline(self):
        pass


###############################################################################
class SSH_ResolveFQDN(SSH_CmdlineParsing):
    suffixes = None
    reverse=False
    gethostbyname_ex = socket.gethostbyname_ex

    def __init__(self, *args, **kwargs):
        """
        the keyword arguments suffixes=[], longest=True, and reverse=True
        are accepted.
        - suffixes provides a list of suffixes to try to resolve against
        - longest specifies that the list of suffixes should be sorted longest to shortest
        - reverse specifies to reverse resolve the address found, and return the resulting name
        """
        self.suffixes = []
        suffixes = kwargs.get('suffixes')
        if suffixes is not None:
            self.suffixes.extend(suffixes)
        self.suffixes.extend([''])

        if kwargs.get('longest'):
            self.suffixes.sort(key=len, reverse=True)

        self.reverse = kwargs.get('reverse')

        super(SSH_ResolveFQDN,self).__init__(*args)
        return

    def find_fqdn(self, hostname):
        """ resolve a matching fqdn """
        try:
            if socket.inet_ntoa(socket.inet_aton(hostname)) == hostname:
                return hostname
        except socket.error:
            pass

        for suffix in self.suffixes:
            testname = hostname + suffix
            try:
                (name, aliaslist, addresslist) = self.gethostbyname_ex(testname)
            except socket.gaierror:
                continue
            else:
                if self.reverse:
                    return name
                return testname
        return hostname

    def update_cmdline(self):
        """ update cmdline by changing self.hostname """
        self.hostname = self.find_fqdn(self.hostname)


class SSH_LocalPortForwardFQDN(SSH_ResolveFQDN):
    """
    Update hostnames used in local port-forwardings
    """
    def update_cmdline(self):
        if '-L' in self.opts:
            n = 0
            for spec in self.opts['-L'].values:
                (local_port, host, remote_port) = spec.split(':')
                self.opts['-L'].values[n] = local_port + ':' + self.find_fqdn(host) + ':' + remote_port
                n += 1

class SSH_RemotePortForwardFQDN(SSH_ResolveFQDN):
    """
    Update hostnames used in remote port-forwardings
    """
    def update_cmdline(self):
        if '-R' in self.opts:
            n = 0
            for spec in self.opts['-R'].values:
                (local_port, host, remote_port) = spec.split(':')
                self.opts['-R'].values[n] = local_port + ':' + self.find_fqdn(host) + ':' + remote_port
                n += 1
