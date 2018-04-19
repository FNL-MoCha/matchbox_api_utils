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

    Basic connector class to make a call to the API and load the raw data. From
    here we pass data, current MatchData or TreatmentArm data to appropiate
    calling classes.

    Used for calling to the MATCHBox API, loading data and, creating a basic 
    data structure. Can load a raw MATCHBox API dataset JSON file, or create 
    one.  Requires credentials, generally acquired from the config file generated 
    upon package setup.

    # TODO: need to update docs.
    Args:
        url (str): API URL for MATCHbox. Generally only using one at the moment,
            but possible to add others later.

        creds (dict): Username and Password credentials obtained from the config
            file generated upon setup. Can also just input a dict in the form 
            of: :: 

                { 'username' : <username>, 'password' : <password> }

        connection (dict): Auth0 client ID  and connection name for the system you 
            are trying to access. This should match the input URL and is system 
            specific (i.e. there is a different one for Adult-MATCHbox, 
            Adult-MATCHbox-UAT, Ped-MATCHBox, etc.).

        make_raw (str): Make a raw, unprocessed MATCHBox API JSON file. Default
            filename will be raw_mb_obj (raw MB patient dataset) or raw_ta_obj (
            raw treatment arm dataset) followed by a datestring. Inputting a
            a string will save the file with the requested filename.

    Returns:
        MATCHBox API dataset, used in ``MatchData`` or ``TreatmentArm`` classes.

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
                sys.stderr.write("** DEBUG: Making synchronous HTTP request. **\n")
            self.api_data = self.__api_call()
        elif self._method == 'async':
            if not self._quiet:
                sys.stderr.write("** DEBUG: Making an asynchronous HTTP request. "
                    "**\n")
            loop = asyncio.get_event_loop()
            self.api_data = loop.run_until_complete(self.__async_caller())

        if not self._quiet:
            sys.stdout.write("Completed the call successfully!\n")
            sys.stdout.write('    -> return len: %s\n' % str(len(self.api_data)))

        # For debugging purposes, we may want to dump the whole raw dataset out 
        # to see what keys / vals are availble.  
        today = utils.get_today('short')
        if make_raw:
            if make_raw == 'mb': 
                filename = 'raw_mb_dump_' + today + '.json'
            elif make_raw == 'ta':
                filename = 'raw_ta_dump_' + today + '.json'
            else:
                sys.stderr.write('ERROR: You must choose from "mb" or "ta" '
                    'only.\n')
                return None

            sys.stdout.write('Making a raw MATCHBox API dump that can be loaded '
                'for development purposes\nrather than a live call to MATCHBox '
                'prior to parsing and filtering.\n')
            utils.make_json(outfile=filename, data=self.api_data, sort=True)
            sys.exit()

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
        
    async def __async_caller(self):
        # Set up an asynchronous method to make HTTP requests in order to get the 
        # DB quicker. 
        gathered_data = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(executor, self.__api_call, page)
                for page in range(1, 20)
            ]
            for response in await asyncio.gather(*futures):
                gathered_data.extend(response)
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
        response = requests.post(url, data = body)
        # TODO: What kinds of errors do we need to handle and how should we handle
        #       them?  Also, what about the fluke times when the request fails; can
        #       we set up a few iterations just to make sure we get a token?
        try:
            response.raise_for_status()
        except HTTPError as error:
            print("got an error!")
            raise
        except:
            raise

        json_data = response.json()
        return json_data['id_token']
