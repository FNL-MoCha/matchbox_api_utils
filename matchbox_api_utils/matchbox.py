# -*- coding: utf-8 -*-
import os
import sys
import json
import requests
import subprocess

from matchbox_api_utils import utils


class Matchbox(object):

    """
    **MATCHBox API Connector Class**

    Basic connector class to make a call to the API and load the raw data. 
    Used for calling to the MATCHBox API, loading data, and passing along to
    the appropriate calling classes for making a basic data structure. Can 
    load a raw MATCHBox API dataset JSON file, or create one.  Requires 
    credentials, generally acquired from the config file generated upon 
    package setup.

    Args:
        url (str): API URL for MATCHbox. This will be specific to the system
            for which you are connecting, and is defined in the config file.

        username (str): Username required for access to MATCHBox. Typically 
            this is already present in the config file made during setup, but
            in cases where needed, it can be explicitly defined here.

        password (str): Password associatd with the user.  As with the above
            username argument, this is typically configured at setup.

        client_name (str): Official Auth0 recognized client name for the 
             MATCHBox to which you are connecting.  This is usually defined
             in the configuration file generated at setup.

        client_id (str): Official Auth0 recognized client id string for the 
             MATCHBox to which you are connecting.  As with the client name,
             this is established in the configuration file typically.

        params (dict): Parameters to pass along to the API in the request. For
            example, if you wanted to add "&is_oa=True" to the API URL, you can
            add: ::

                ``params = {'is_oa' : True}``

            and this will be passed along to the request.

        make_raw (str): Make a raw, unprocessed MATCHBox API JSON file. Default
            filename will be raw_mb_obj (raw MB patient dataset) or raw_ta_obj (
            raw treatment arm dataset) followed by a datestring. Inputting a
            a string will save the file with the requested filename.

        quiet (bool): Suppress debug and information messages.

    """

    def __init__(self, method, config, params=None, mongo_collection=None, 
        make_raw=None, quiet=False):
        '''
            method: str ('mongo', or 'api')
            config: dict Contains all of the information necessary for the
                connection.
        '''
        self._params = params
        self._quiet = quiet
        self.today = utils.get_today('short')
        self.api_data = []

        if method == 'api':
            sys.stderr.write("WARN: API calls are soon to be deprecated. Please "
                "transition to MongoDB calls.\n")

            self._url = config.get('url', None)
            self._username = config.get('username', None)
            self._password = config.get('password', None)
            self._client_name = config.get('client_name', None)
            self._client_id = config.get('client_id', None)

            self._token = self.__get_token()
            # TODO: Remove this. to be replaced by a mongodb call.
            for page in range(1, 15):
                self.api_data += self.__api_call(page)
            if not self._quiet:
                sys.stdout.write("Completed the call successfully!\n")
                sys.stdout.write('   -> return len: %s\n' % str(
                    len(self.api_data))
                )
            if make_raw:
                # TODO:  Clean this up a bit.  Need to handle a "make_raw" call 
                #        in both methods.  Make a function and handle wiht args.
                raw_files = {
                    'mb' : 'raw_mb_dump_%s.json' % self.today,
                    'ta' : 'raw_ta_dump_%s.json' % self.today
                }
                try:
                    filename = raw_files[make_raw]
                except KeyError:
                    sys.stderr.write('ERROR: You must choose from "mb" or "ta" '
                        'only when using the "make_raw" argument.\n')
                    return None

                sys.stdout.write('Making a raw MATCHBox API dump that can be '
                    'loaded for development purposes\nrather than a live call '
                    'to MATCHBox prior to parsing and filtering.\n')
                utils.make_json(outfile=filename, data=self.api_data, sort=True)
                return
        elif method == 'mongo':
            # Only keep patient in here for now.  Will add more as we go.
            collections = ('patient')
            if mongo_collection is None:
                sys.stderr.write('ERROR: You must input a collection when '
                    'making the MongoDB call.\n')
                return None
            elif mongo_collection not in collections:
                sys.stderr.write('ERROR: collection %s is not valid. Please '
                    'only choose from:\n')
                sys.stderr.write('\n'.join(collections))

            outfile = 'raw_%s_dump_%s.json' % (mongo_collection, self.today)
            self._mongo_user = config.get('mongo_user', None)
            self._mongo_pass = config.get('mongo_pass', None)
            self.api_data = self.__mongo_call(mongo_collection, outfile)
            if make_raw is None:
                os.remove(outfile)
        else:
            sys.stderr.write('ERROR: method %s is not a valid method! Choose '
                'only from "api" or "mongo".\n')
            return None


    def __str__(self):
        return utils.print_json(self.api_data)

    def __mongo_call(self, collection, outfile):
        '''
        Now the better way to get a whole DB dump is to make a call to the 
        MongoDB directly.  Will need different creds for this that may not be
        easily obtained for all users, and it may be more difficult to get 
        smaller bits of data, so I'll leave the API call in here.  But, for main
        data export / import, I will start calling this instead now.
        '''

        cmd = [
            'mongoexport',
            '--host', 'adultmatch-production-shard-00-00-tnrm0.mongodb.net:27017,adultmatch-production-shard-00-01-tnrm0.mongodb.net:27017,adultmatch-production-shard-00-02-tnrm0.mongodb.net:27017',
            '--ssl',
            '--username', self._mongo_user,
            '--password', self._mongo_pass,
            '--authenticationDatabase', 'admin',
            '--db', 'Match',
            '--collection', collection,
            '--type', 'json', '--jsonArray',
            '--out', outfile
        ]

        tries = 0
        while tries < 4:
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, 
                stdout=subprocess.PIPE)
            out, err = p.communicate()
            tries += 1
            if p.returncode != 0:
                sys.stderr.write('Error getting data from mongoDB. Trying '
                    'again ({}/{} tries).\n'.format(tries, '4'))
                # TODO: have this output to debug log.
                # sys.stderr.write(err.decode('utf-8'))
                sys.stderr.flush()
            else:
                if self._quiet is False:
                    sys.stderr.write('Completed the Mongo export call '
                        'successfully.\n')
                    sys.stderr.flush()
                break
        self.api_data = utils.read_json(outfile)

    def __api_call(self, page=None):
        header = {'Authorization' : 'bearer %s' % self._token}
        # For async page requests, will need to update the page number for each 
        # loop.
        if page is not None:
            self._params['page'] = page 

        response = requests.get(self._url, params=self._params, headers=header)
        
        # DEBUG XXX: remove me
        '''
        print('-'*75)
        print(response.links)
        print(response.headers)
        print('page {} -> {}'.format(page, response.url))
        print('status: {}; total returned: {}'.format(response.status_code,
            len(response.json())))
        # print(len(response.json()))
        print(response.json()[0].keys())
        print('-'*75)
        '''

        try: 
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            sys.stderr.write('ERROR: Can not access MATCHBox data. Got error: '
                '%s\n' % e)
            sys.exit(1)
        return response.json()
        
    def __get_token(self):
        body = {
            "client_id" : self._client_id,
            "username" : self._username,
            "password" : self._password,
            "grant_type" : "password",
            "scope" : "openid roles email profile",
            "connection" : self._client_name,
        }
        url = 'https://ncimatch.auth0.com/oauth/ro'
        counter = 0
        while counter < 4:  # Keep it to three attempts.
            counter += 1
            response = requests.post(url, data = body)
            try:
                response.raise_for_status()
                break
            except HTTPError as error:
                sys.stderr.write("ERROR: Got an error trying to get an Auth0 "
                    "token! Attempt %s of 3.\n" % counter)
                continue
            except:
                raise

        json_data = response.json()
        return json_data['id_token']
