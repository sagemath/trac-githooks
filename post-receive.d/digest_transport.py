r"""
HTTP transport to the trac server

AUTHORS:

- David Roe, Julian Rueth, Robert Bradshaw: initial version

"""
#*****************************************************************************
#       Copyright (C) 2013 David Roe <roed.math@gmail.com>
#                          Julian Rueth <julian.rueth@fsfe.org>
#                          Robert Bradshaw <robertwb@gmail.com>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#  as published by the Free Software Foundation; either version 2 of
#  the License, or (at your option) any later version.
#                  http://www.gnu.org/licenses/
#*****************************************************************************

from xmlrpclib import SafeTransport, Fault
import urllib2

class TracError(RuntimeError):
    pass

class TracConnectionError(TracError):
    def __init__(self, msg=None):
        if msg is None:
            TracError.__init__(self, 'Connection to trac server failed.')
        else:
            TracError.__init__(self, msg)


class TracInternalError(TracError):
    def __init__(self, fault):
        self._fault = fault
        self.faultCode = fault.faultCode

    def __str__(self):
        return str(self._fault)


class TracAuthenticationError(TracError):
    def __init__(self):
        TracError.__init__(self, 'Authentication with trac server failed.')

class DigestTransport(object, SafeTransport):
    """
    Handles an HTTP transaction to an XML-RPC server.

    EXAMPLES::

        sage: from sage.dev.digest_transport import DigestTransport
        sage: DigestTransport()
        <sage.dev.digest_transport.DigestTransport object at ...>

    """
    def __init__(self):
        """
        Initialization.

        EXAMPLES::

            sage: from sage.dev.digest_transport import DigestTransport
            sage: type(DigestTransport())
            <class 'sage.dev.digest_transport.DigestTransport'>

        """
        SafeTransport.__init__(self)

        self._opener = None

    @property
    def opener(self):
        """
        Create an opener object.

        By calling :meth:`add_authentication` before calling this property for
        the first time, authentication credentials can be set.

        EXAMPLES::

            sage: from sage.dev.digest_transport import DigestTransport
            sage: DigestTransport().opener
            <urllib2.OpenerDirector instance at 0x...>

        """
        if self._opener is None:
            self._opener = urllib2.build_opener(urllib2.HTTPDigestAuthHandler())
        return self._opener

    def add_authentication(self, realm, url, username, password):
        """
        Set authentication credentials for the opener returned by
        :meth:`opener`.

        EXAMPLES::

            sage: from sage.dev.digest_transport import DigestTransport
            sage: dt = DigestTransport()
            sage: dt.add_authentication("realm", "url", "username", "password")
            sage: dt.opener
            <urllib2.OpenerDirector instance at 0x...>

        """
        assert self._opener is None

        authhandler = urllib2.HTTPDigestAuthHandler()
        authhandler.add_password(realm,url,username,password)
        self._opener = urllib2.build_opener(authhandler)

    def single_request(self, host, handler, request_body, verbose):
        """
        Issue an XML-RPC request.

        EXAMPLES::

            sage: from sage.dev.digest_transport import DigestTransport
            sage: from sage.env import TRAC_SERVER_URI
            sage: import urlparse
            sage: url = urlparse.urlparse(TRAC_SERVER_URI).netloc
            sage: d = DigestTransport()
            sage: d.single_request(url, 'xmlrpc', "<?xml version='1.0'?><methodCall><methodName>ticket.get</methodName><params><param><value><int>1000</int></value></param></params></methodCall>", 0) # optional: internet
            ([1000,
              <DateTime '20071025T16:48:05' at ...>,
              <DateTime '20080110T08:28:40' at ...>,
              {'status': 'closed',
               'changetime': <DateTime '20080110T08:28:40' at ...>,
               'description': '',
               'reporter': 'was',
               'cc': '',
               'type': 'defect',
               'milestone': 'sage-2.10',
               '_ts': '1199953720000000',
               'component': 'distribution',
               'summary': 'Sage does not have 10000 users yet.',
               'priority': 'major',
               'owner': 'was',
               'time': <DateTime '20071025T16:48:05' at ...>,
               'keywords': '',
               'resolution': 'fixed'}],)

        """
        try:
            import urlparse
            req = urllib2.Request(
                    urlparse.urlunparse(('https', host, handler, '', '', '')),
                    request_body, {'Content-Type': 'text/xml',
                        'User-Agent': self.user_agent})

            response = self.opener.open(req)

            self.verbose = verbose
            return self.parse_response(response)
        except Fault as e:
            raise TracInternalError(e)
        except urllib2.HTTPError as e:
            if e.code == 401:
                raise TracAuthenticationError()
            else:
                raise TracConnectionError(e.reason)
