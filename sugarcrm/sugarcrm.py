#
#   sugarcrm.py
#
#   KSU capstone project
#

import urllib
import hashlib
import json
import sys

from sugarerror import SugarError, SugarUnhandledException, is_error
from sugarmodule import *

class Sugarcrm:
    """Sugarcrm main interface class.

    This class is what is used to connect to and interact with the SugarCRM
    server.
    """
    
    def __init__(self, url, username, password):
        """Constructor for Sugarcrm connection.

        Keyword arguments:
        url -- string URL of the sugarcrm REST API
        username -- username to allow login upon construction
        password -- password to allow login upon construction
        """

        # String which holds the session id of the connection, required at
        # every call after 'login'.
        self._session = ""

        # url which is is called every time a request is made.
        self._url = url

        self._username = username
        self._password = password

        # Attempt to login.
        self._login(username, password)

        # Dynamically add the API methods to the object.
        for method in ['get_user_id', 'get_user_team_id',
                       'get_available_modules', 'get_module_fields',
                       'get_entries_count', 'get_entry', 'get_entries',
                       'get_entry_list', 'set_entry', 'set_entries',
                       'set_relationship', 'set_relationships',
                       'get_relationships', 'get_server_info',
                       'set_note_attachment', 'get_note_attachment',
                       'set_document_revision', 'get_document_revision',
                       'search_by_module', 'get_report_entries', 'logout']:
            # Use this to be able to evaluate "method".
            def gen(method_name):
                def f(*args):
                    try:
                        result = self._sendRequest(method_name,
                                              [self._session] + list(args))
                    except SugarError, error:
                        if error.is_invalid_session():
                            # Try to recover if session ID was lost
                            self._login(self._username, self._password)
                            result = self._sendRequest(method_name,
                                              [self._session] + list(args))
                        elif error.is_missing_module():
                            return None
                        elif error.is_null_response():
                            return None
                        else:
                            raise SugarUnhandledException

                    return result
                f.__name__ = method
                return f
            self.__dict__[method] = gen(method)

        # Add modules containers
        self.modules = {}
        self.rst_modules = dict((m['module_key'], m)
                                for m in self.get_available_modules()['modules'])
    def __getitem__(self, key):
        if key not in self.rst_modules:
            raise KeyError("Invalid Key '%s'" % key)
        if key in self.rst_modules and key not in self.modules:
            self.modules[key] = SugarModule(self, key)
        return self.modules[key]

    def _sendRequest(self, method, data):
        """Sends an API request to the server, returns a dictionary with the
        server's response.

        It should not need to be called explicitly by the user, but rather by
        the other functions.

        Keyword arguments:
        method -- name of the method being called.
        data -- parameters to the function being called, should be in a list
                sorted by order of items
        """

        data = json.dumps(data)
        args = {'method': method, 'input_type': 'json',
                'response_type' : 'json', 'rest_data' : data}
        params = urllib.urlencode(args)
        response = urllib.urlopen(self._url, params)
        response = response.read().strip()

        if not response:
            raise SugarError({'name': 'Empty Result',
                              'description': 'No data from SugarCRM.',
                              'number': 0})

        result = json.loads(response)

        if is_error(result):
            raise SugarError(result)

        return result


    def _login(self, username, password):
        """Estabilsh connection to the server.

        Keyword arguments:
        username -- SugarCRM user name.
        password -- plaintext string of the user's password.
        """

        args = {'user_auth' : {'user_name' : username,
                               'password' : _passencode(password)}}

        x = self._sendRequest('login', args)
        try:
            self._session = x["id"]
        except KeyError:
            raise SugarUnhandledException


    def relate(self, main, *secondary):
        """Relate two SugarEntry objects."""
        args = [[main._module._name] * len(secondary),
                [main['id']] * len(secondary),
                [s._module._table for s in secondary],
                [[s['id']] for s in secondary]]
        # Required for Sugar Bug 32064.
        if main._module._name == 'ProductBundles':
            args.append([[{'name': 'product_index',
                          'value': '%d' % (i + 1)}] for i in range(len(secondary))])
        self.set_relationships(*args)


def _passencode(password):
    """Returns md5 hash to send as a password.

    Keyword arguments:
    password -- string to be encoded
    """

    encode = hashlib.md5(password)
    result = encode.hexdigest()

    return result

