# Maestro is Copyright (C) 2006-2008 by Infiscape Corporation
#
# Original Author: Aron Bierbaum
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import logging
import sspi, sspicon
import win32api, win32security, ntsecuritycon
import pywintypes
from twisted.spread import pb
from twisted.spread.interfaces import IJellyable
import twisted.python.failure as failure
import twisted.cred.error as error

import maestro.daemon.avatar as avatar
import maestro.core.plugin_interfaces as PI


class SspiAuthenticationServer:
   id = 'ntlm'

   def __init__(self, broker, pkgName):
      PI.IServerAuthenticationPlugin.__init__(self, broker)

      flags = sspicon.ASC_REQ_INTEGRITY       | \
              sspicon.ASC_REQ_SEQUENCE_DETECT | \
              sspicon.ASC_REQ_REPLAY_DETECT   | \
              sspicon.ASC_REQ_CONFIDENTIALITY | \
              sspicon.ASC_REQ_DELEGATE
      self.mServer = sspi.ServerAuth(pkgName, scflags = flags)
      self.mLogger = logging.getLogger('maestrod.auth.%s' % pkgName)

   def remote_authorize(self, data):
      err, sec_buffer = self.mServer.authorize(data)

      if err == 0:
         # Get the handle for the authenticated user such that we can pass it
         # to win32security.DuplicateTokenEx() and get back a handle that
         # allows us to spawn interactive processes as the authenticated user.
         self.mServer.ctxt.ImpersonateSecurityContext()
         flags = win32security.TOKEN_DUPLICATE | win32security.TOKEN_QUERY
         handle = win32security.OpenThreadToken(win32api.GetCurrentThread(),
                                                flags, False)
         self.mServer.ctxt.RevertSecurityContext()

         # Using handle, reate a primary handle suitable for passing to
         # CreateProcessAsUser().
         sec_attr = None
#         sec_attr = pywintypes.SECURITY_ATTRIBUTES()
#         sec_attr.Initialize()
#         sec_attr.bInheritHandle = True

         # Try different impersonation levels for DuplicateTokenEx(). These
         # should be in order of decreasing utility (most useful to least).
         # See the SECURITY_IMPERSONATION_LEVEL documentation for more
         # details.
         levels = [win32security.SecurityDelegation,
                   win32security.SecurityImpersonation]

         primary_handle = None
         #access = win32security.TOKEN_ALL_ACCESS
         #access = win32con.MAXIMUM_ALLOWED
         access = win32security.TOKEN_IMPERSONATE    | \
                  win32security.TOKEN_QUERY          | \
                  win32security.TOKEN_ASSIGN_PRIMARY | \
                  win32security.TOKEN_DUPLICATE

         for l in levels:
            try:
               primary_handle = \
                  win32security.DuplicateTokenEx(
                     ExistingToken = handle,
                     DesiredAccess = access,
                     ImpersonationLevel = l,
                     TokenType = ntsecuritycon.TokenPrimary,
                     TokenAttributes = sec_attr
                  )
               break
            except Exception, ex:
               self.mLogger.error("Failed to create primary token with impersonation level %s:" % str(l))
               self.mLogger.error(str(ex))

         # If the above failed to create a primary token, then we throw an
         # exception. It is important that we do not return None from this
         # method.
         if primary_handle is None:
            msg = 'Failed to create primary token for user!'
            self.mLogger.error(msg)
            raise failure.Failure(error.UnauthorizedLogin(msg))

         # acct_info[0] has the SID for the user.
         acct_info = win32security.GetTokenInformation(primary_handle,
                                                       win32security.TokenUser)
         user_sid  = acct_info[0]

         # This returns a tuple containing the user name, the domain (if
         # applicable), and the accouunt type.
         # NOTE: The returned strings may be Unicode strings.
         user_info = win32security.LookupAccountSid(None, user_sid)

         # Close the handle returned by win32security.OpenThreadToken() since
         # it is a duplicate.
         handle.Close()

         # NOTE: We are forcing the addition of user_sid to the window station
         # and desktop ACLs. This seems to be the only way for the user
         # authenticated through SSPI to be able to open interactive windows.
         return self.prepareAvatar(avatar.WindowsAvatar(primary_handle,
                                                        user_sid,
                                                        str(user_info[0]),
                                                        str(user_info[1]),
                                                        True))

      return sec_buffer[0].Buffer

class NtlmAuthenticationServer(PI.IServerAuthenticationPlugin,
                               SspiAuthenticationServer):
   id = 'sspi_ntlm'

   def __init__(self, broker):
      SspiAuthenticationServer.__init__(self, broker, 'NTLM')

class KerberosAuthenticationServer(PI.IServerAuthenticationPlugin,
                                   SspiAuthenticationServer):
   id = 'sspi_kerberos'

   def __init__(self, broker):
      SspiAuthenticationServer.__init__(self, broker, 'Kerberos')

# XXX: This is disabled until we figure out what the SSPI package name for
# Schannel is supposed to be. The values 'Schannel', 'schannel', and 'ssl'
# have been tried. Perhaps the problem is that I just don't have SSPI/SChannel
# available at all.
#class SSLAuthenticationServer(PI.IServerAuthenticationPlugin,
#                              SspiAuthenticationServer):
#   id = 'sspi_ssl'
#
#   def __init__(self, broker):
#      SspiAuthenticationServer.__init__(self, broker, 'Schannel')

class NegotiatedAuthenticationServer(PI.IServerAuthenticationPlugin,
                                     SspiAuthenticationServer):
   id = 'sspi_negotiate'

   def __init__(self, broker):
      SspiAuthenticationServer.__init__(self, broker, 'Negotiate')
