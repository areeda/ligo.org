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

"""Tests for :mod:`ligo.org.utils`
"""

try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
    urlreqmodname = "urllib2"
else:
    urlreqmodname = "urllib.request"

import pytest

from .. import utils as ligodotorg_utils

__author__ = 'Duncan Macleod <duncan.macleod@ligo.org>'

RAW_INSTITUTION_LIST = [
    b"https://inst1.test Institution 1",
    b"https://inst2.test Institution 2",
]


@mock.patch(
    "{}.urlopen".format(urlreqmodname),
    return_value=RAW_INSTITUTION_LIST,
)
def test_get_idps(urlopen):
    assert ligodotorg_utils.get_idps("something", extras=False) == {
        "Institution 1": "https://inst1.test",
        "Institution 2": "https://inst2.test",
    }
    assert urlopen.called_with("something")


@mock.patch(
    "{}.urlopen".format(urlreqmodname),
    return_value=RAW_INSTITUTION_LIST,
)
def test_get_idps_extras(_):
    idps = ligodotorg_utils.get_idps("something", extras=True)
    assert idps["Cardiff University"] == (
        "https://idp.cf.ac.uk/idp/profile/SAML2/SOAP/ECP"
    )


@mock.patch(
    "{}.urlopen".format(urlreqmodname),
    return_value=RAW_INSTITUTION_LIST,
)
def test_get_idp_urls(_):
    assert ligodotorg_utils.get_idp_urls("Institution 1") == (
        "https://inst1.test",
        "https://inst1.test",
    )


@mock.patch(
    "{}.urlopen".format(urlreqmodname),
    return_value=RAW_INSTITUTION_LIST,
)
@pytest.mark.parametrize("inst", ["Institution*", "something else"])
def test_get_idp_urls_error(_, inst):
    with pytest.raises(ValueError):
        ligodotorg_utils.get_idp_urls(inst)


@pytest.mark.parametrize("url, result", [
    ("login.ligo.org", "https://login.ligo.org/idp/profile/SAML2/SOAP/ECP"),
    ("login.ligo.org/test", "https://login.ligo.org/test"),
    ("https://login.ligo.org/idp/profile/SAML2/SOAP/ECP",
     "https://login.ligo.org/idp/profile/SAML2/SOAP/ECP"),
])
def test_format_endpoint_url(url, result):
    assert ligodotorg_utils.format_endpoint_url(url) == result
