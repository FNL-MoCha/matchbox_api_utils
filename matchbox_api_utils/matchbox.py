# -*- coding: utf-8 -*-
import os
import sys
import json
import asyncio
import concurrent.futures
import requests

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

        method (str): Method by which we'll make HTTP requests to the client.
            Valid values are 'sync' for synchronous requests (usually when 
            there is only one request to be made), or 'async' for asynchronous
            requests (usually when we're trying to get the whole DB and have
            to make many calls to the server).

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

    def __init__(self, url, username, password, client_name, client_id, 
            method='sync', params=None, make_raw=None, quiet=True):

        self._url = url
        self._username = username
        self._password = password
        self._client_name = client_name
        self._client_id = client_id
        self._params = params
        self._quiet = quiet
        self._method = method
        self._token = self.__get_token()

        if self._method == 'sync':
            if not self._quiet:
                sys.stderr.write("** DEBUG: Making synchronous HTTP request. "
                    "**\n")
            self.api_data = self.__api_call()
        elif self._method == 'async':
            if not self._quiet:
                sys.stderr.write("** DEBUG: Making an asynchronous HTTP "
                    "request.  **\n")
            loop = asyncio.get_event_loop()
            self.api_data = loop.run_until_complete(self.__async_caller(loop))

        if not self._quiet:
            sys.stdout.write("Completed the call successfully!\n")
            sys.stdout.write('   -> return len: %s\n' % str(len(self.api_data)))

        # For debugging purposes, we may want to dump the whole raw dataset out 
        # to see what keys / vals are availble.  
        today = utils.get_today('short')
        raw_files = {
            'mb' : 'raw_mb_dump_' + today + '.json',
            'ta' : 'raw_ta_dump_' + today + '.json',
        }
        if make_raw:
            try:
                filename = raw_files[make_raw]
            except KeyError:
                sys.stderr.write('ERROR: You must choose from "mb" or "ta" '
                    'only when using the "make_raw" argument.\n')
                return None

            sys.stdout.write('Making a raw MATCHBox API dump that can be '
                'loaded for development purposes\nrather than a live call to '
                'MATCHBox prior to parsing and filtering.\n')
            utils.make_json(outfile=filename, data=self.api_data, sort=True)
            return

    def __str__(self):
        return utils.print_json(self.api_data)

    def __api_call(self, page=None):
        header = {'Authorization' : 'bearer %s' % self._token}
        # For async page requests, will need to update the page number for each 
        # loop.
        if page is not None:
            self._params['page'] = page 

        response = requests.get(self._url, params=self._params, headers=header)
        try: 
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            sys.stderr.write('ERROR: Can not access MATCHBox data. Got error: '
                '%s\n' % e)
            sys.exit(1)
        return response.json()
        
    async def __async_caller(self, loop):
        # Set up an asynchronous method to make HTTP requests in order to get 
        # the DB more quickly. 
        gathered_data = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
            futures = [
                loop.run_in_executor(executor, self.__api_call, page)
                for page in range(1, 21)
            ]
            for response in await asyncio.gather(*futures):
                gathered_data.extend(response)
                gathered_data+=response
        return gathered_data

    def __get_token(self):
        body = {
            "client_id" : self._client_id,
            "username" : self._username,
            "password" : self._password,
            "grant_type" : "password",
            "scope" : "openid roles email",
            "connection" : self._client_name,
        }
        url = 'https://ncimatch.auth0.com/oauth/ro'
        counter = 0
        while counter < 4:  # Keep it to three attempts.
            counter += 1
            response = requests.post(url, data = body)
            # TODO: Figure out what other kinds of error we might encounter,
            #       and try to handle them appropriately.
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
