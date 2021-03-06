# -*- coding: utf-8 -*-
# Copyright (C) Duncan Macleod (2019)
#
# This file is part of LIGO.ORG.
#
# LIGO.ORG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LIGO.ORG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LIGO.ORG.  If not, see <http://www.gnu.org/licenses/>.

import platform
import random
import re
import ssl
import string
from getpass import getpass
from pathlib import Path
try:
    from urllib import request as urllib_request
    from urllib.parse import urlparse
except ImportError:  # python < 3
    import urllib2 as urllib_request
    from urlparse import urlparse
    input = raw_input  # noqa: F821

# extra institutions not known by CILogon
EXTRA_INSTITUTIONS = {
    # LIGO IdPs
    "LIGO.ORG":
        "https://login.ligo.org/idp/profile/SAML2/SOAP/ECP",
    "LIGOGuest":
        "https://login.guest.ligo.org/idp/profile/SAML2/SOAP/ECP",
    "DEV.LIGO.ORG":
        "https://login-dev.ligo.org/idp/profile/SAML2/SOAP/ECP",
    "TEST.LIGO.ORG":
        "https://login-test.ligo.org/idp/profile/SAML2/SOAP/ECP",
    # extra institutions
    "Cardiff University":
        "https://idp.cf.ac.uk/idp/profile/SAML2/SOAP/ECP",
    "Syracuse University":
        "https://sugwg-login.phy.syr.edu/idp/profile/SAML2/SOAP/ECP",
}

# -- default CA files ---------------------------------------------------------

DEFAULT_VERIFY_PATHS = ssl.get_default_verify_paths()


def _defaults():
    if platform.system() in {"Windows", "Darwin"}:
        return DEFAULT_VERIFY_PATHS.cafile, DEFAULT_VERIFY_PATHS.capath

    # -- on Linux we can be a bit more discerning

    # always prefer python's default cafile
    for path in (
        DEFAULT_VERIFY_PATHS.cafile,
        "/etc/ssl/certs/ca-certificates.crt",  # debian
        "/etc/pki/tls/cert.pem",
    ):
        if Path(path or "").is_file():
            cafile = path
            break
    else:
        cafile = None

    # prefer globus certificates path
    globusdir = "/etc/grid-security/certificates"
    if Path(globusdir).is_dir():
        return cafile, globusdir

    return cafile, DEFAULT_VERIFY_PATHS.capath


DEFAULT_CAFILE, DEFAULT_CAPATH = _defaults()


# -- institution URLs ----------------------------------------------------

DEFAULT_IDPLIST_URL = "https://cilogon.org/include/ecpidps.txt"
DEFAULT_SP_URL = "https://ecp.cilogon.org/secure/getcert"
KERBEROS_SUFFIX = " (Kerberos)"
KERBEROS_REGEX = re.compile(r"{}\Z".format(re.escape(KERBEROS_SUFFIX)))


def get_idps(url=DEFAULT_IDPLIST_URL, extras=True):
    """Download the list of known ECP IdPs from the given URL

    The output is a `dict` where the keys are institution names
    (e.g. ``'Fermi National Accelerator Laboratory'``), and the values
    are the URL of their IdP.

    Some institutions may have two entries if they also support Kerberos.

    Parameters
    ----------
    url : `str`
        the URL of the IDP list file

    extras : `bool`, optional
        if `True` (default), include the extra IdP URLs known in this
        package, otherwise include only those from the remote IdP list
    """
    idps = EXTRA_INSTITUTIONS.copy() if extras else dict()
    for line in urllib_request.urlopen(url):
        url, inst = line.decode('utf-8').strip().split(' ', 1)
        idps[inst] = url
    return idps


def _match_institution(value, institutions):
    regex = re.compile(r"{0}($| \()".format(value))
    institutions = {KERBEROS_REGEX.split(name, 1)[0] for name in institutions}
    matches = [inst for inst in institutions if regex.match(inst)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0 and not value.endswith(".*"):
        try:
            return _match_institution("{}.*".format(value), institutions)
        except ValueError:
            pass
    raise ValueError("failed to identify IdP URLs for {!r}".format(value))


def get_idp_urls(institution, url=DEFAULT_IDPLIST_URL):
    """Return the regular and Kerberos IdP URLs for a given institution
    """
    idps = get_idps(url=url)
    institution = _match_institution(institution, idps)
    if institution.endswith(KERBEROS_SUFFIX):
        return None, idps[institution]
    url = idps[institution]
    krbinst = institution + KERBEROS_SUFFIX
    krburl = idps[krbinst] if krbinst in idps else url
    return url, krburl


def _endpoint_url(url):
    if "/" not in url:
        url = "https://{}/idp/profile/SAML2/SOAP/ECP".format(url)
    if not urlparse(url).scheme:
        url = "https://{}".format(url)
    return url


def format_endpoint_url(url_or_name, kerberos=False):
    """Format an endpoint reference as a URL

    Parameters
    ----------
    url_or_name: `str`
        the name of an institution, or a URL for the endpoint

    kerberos : `bool`, optional
        if ``True`` return a Kerberos URL, if available, otherwise return
        a standard SAML/ECP endpoint URL

    Returns
    -------
    url : `str`
        the formatted URL of the IdP ECP endpoint

    Raises
    ------
    ValueError
        if ``url_or_name`` looks like an institution name, but
        cilogon.org doesn't know what the corresponding ECP endpoint URL
        is for that institution.

    Examples
    --------
    >>> format_endpoint_url("LIGO")
    'https://login.ligo.org/idp/profile/SAML2/SOAP/ECP'
    >>> format_endpoint_url("login.myidp.com")
    'https://login.myidp.com/idp/profile/SAML2/SOAP/ECP'
    """
    if url_or_name.count(".") >= 2:  # url
        return _endpoint_url(url_or_name)
    # institution name
    return get_idp_urls(url_or_name)[int(kerberos)]


# -- misc utilities -----------------------------------------------------------

def random_string(length, outof=string.ascii_lowercase+string.digits):
    # http://stackoverflow.com/a/23728630/2213647 says SystemRandom()
    # is most secure
    return ''.join(random.SystemRandom().choice(outof) for _ in range(length))


def prompt_username_password(host, username=None):
    if username is None:
        username = input("Enter username for {}: ".format(host))
    password = getpass(
        "Enter password for {!r} on {}: ".format(username, host),
    )
    return username, password
