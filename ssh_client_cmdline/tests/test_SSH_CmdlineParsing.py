from ssh_client_cmdline import SSH_CmdlineParsing
import unittest
import socket

class mock_resolver(object):
    hostlist = {}

    def __init__(self, hostlist):
        self.hostlist = {}
        self.hostlist.update(hostlist)
        return

    def gethostbyname_ex(self,hostname):
        address = self.hostlist.get(hostname)
        if address:
            return (hostname, [] , [str(address)])
        raise socket.gaierror('[Errno 8] nodename nor servname provided, or not known')

    def __repr__(self):
        return str(self.hostlist)


class testcase(unittest.TestCase):
    def test_splithostname(self):
        a = SSH_CmdlineParsing.SSH_CmdlineParsing( ['user@somehost', 'somecommand'] );
        a.split_hostname()
        self.assertEqual(a._hostname,'somehost')
        self.assertEqual(a._username,'user')
        return

    def test_hostname(self):
        a = SSH_CmdlineParsing.SSH_CmdlineParsing( ['user@somehost', 'somecommand'] );
        self.assertEqual(a.hostname,'somehost')
    
    def test_username(self):
        a = SSH_CmdlineParsing.SSH_CmdlineParsing( ['user@somehost','somecommand'] );
        self.assertEqual(a.username,'user')

    def test_username_opt_prefered(self):
        a = SSH_CmdlineParsing.SSH_CmdlineParsing( ['-l','optuser', 'user@somehost','somecommand'] );
        self.assertEqual(a.username,'user')

    def test_username_opt(self):
        a = SSH_CmdlineParsing.SSH_CmdlineParsing( ['-l','optuser', 'somecommand'] );
        self.assertEqual(a.username,'optuser')

    def test_cmdline(self):
        a = SSH_CmdlineParsing.SSH_CmdlineParsing( ['-l','optuser', 'user@somehost','somecommand'] );
        self.assertEqual(a.cmdline, ['-l','optuser','user@somehost','somecommand'])

    def test_fqdn(self):
        a = SSH_CmdlineParsing.SSH_ResolveFQDN( ['-l','optuser', 'user@localhost','somecommand'] );
        self.assertEqual(a.hostname,'localhost')

    def test_fqdn_suffix(self):
        resolver = mock_resolver( {'localhost.localdomain':'127.0.0.1'} )
        a = SSH_CmdlineParsing.SSH_ResolveFQDN( ['-l','optuser', 'user@localhost','somecommand'], suffixes=['.localdomain'] );
        a.gethostbyname_ex = resolver.gethostbyname_ex
        a.update_cmdline()
        self.assertEqual(a.hostname,'localhost.localdomain')

    def test_longest(self):
        resolver = mock_resolver({
            'localhost.localgroup.localcluster.localsolarsystem.localdomain':'longest', 
            'localhost.localgroup.localcluster.localsolarsystem':None,
            'localhost.localdomain':None })
        a = SSH_CmdlineParsing.SSH_ResolveFQDN( ['-l','optuser', 'user@localhost','somecommand'], suffixes=[
                    '.localdomain',
                    '.localgroup.localcluster.localsolarsystem',
                    '.localgroup.localcluster.localsolarsystem.localdomain',
                    ], longest=True );
        a.gethostbyname_ex = resolver.gethostbyname_ex
        a.update_cmdline()
        self.assertEqual(a.hostname,'localhost.localgroup.localcluster.localsolarsystem.localdomain')

    def test_local_forward(self):
        resolver = mock_resolver( {'localhost.localdomain':'127.0.0.1'} )
        a = SSH_CmdlineParsing.SSH_LocalPortForwardFQDN( ['-l','optuser', '-L1234:localhost:1234', 'user@localhost','somecommand'], suffixes=['.localdomain'] );
        a.gethostbyname_ex = resolver.gethostbyname_ex
        a.update_cmdline()
        self.assertEqual(a.opts['-L'].values, ['1234:localhost.localdomain:1234'])

    def test_remote_forward(self):
        resolver = mock_resolver( {'localhost.localdomain':'127.0.0.1'} )
        a = SSH_CmdlineParsing.SSH_RemotePortForwardFQDN( ['-l','optuser', '-R1234:localhost:1234', 'user@localhost','somecommand'], suffixes=['.localdomain'] );
        a.gethostbyname_ex = resolver.gethostbyname_ex
        a.update_cmdline()
        self.assertEqual(a.opts['-R'].values, ['1234:localhost.localdomain:1234'])

if __name__ == '__main__':
    unittest.main()
