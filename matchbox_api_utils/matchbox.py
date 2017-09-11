# -*- coding: utf-8 -*-
import os
import sys
import json

import utils

class Matchbox(object):

    """
    MATCHBox API Connector Class.

    Basic connector class to make a call to the API and load the raw data. From
    here we pass data, current MatchData or TreatmentArm data to appropiate calling
    classes.  

    """

    def __init__(self,url,creds,make_raw=None):
        """
        MATCHBox API class. 
        
        Used for calling to the MATCHBox API, loading data and, creating a basic 
        data structure. Can load a raw MATCHBox API dataset JSON file, or create 
        one.  Requires credentials, generally acquired from the config file generated 
        upon package setup.

        Args:
            url (str): API URL for MATCHbox. Generally only using one at the moment,
                       but possible to add others later.
            creds (dict): Username and Password credentials obtained from the config
                          file generated upon setup. Can also just input a dict in 
                          the form of:
                              'username' : <username>,
                              'password' : <password>

            make_raw (str): Make a raw, unprocessed MATCHBox API JSON file. Default
                filename will be raw_mb_obj (raw MB patient dataset) or raw_ta_obj (
                raw treatment arm dataset) followed by a datestring. Inputting a
                a string will save the file with the requested filename.

        Returns:
            MATCHBox API dataset, used in MatchData or TreatmentArm classes.

        """
        self.url   = url
        self.creds = creds
        self.api_data = self.__api_call()

        # For debugging purposes, we may want to dump the whole raw dataset out to see what keys / vals are availble.  
        # today = datetime.date.today().strftime('%m%d%y')
        today = utils.get_today('short')
        if make_raw:
            if make_raw == 'mb': 
                filename = 'raw_mb_dump_' + today + '.json'
            elif make_raw == 'ta':
                filename = 'raw_ta_dump_' + today + '.json'

            sys.stdout.write('Making a raw MATCHBox API dump that can be loaded for development '
                    'purposes rather than a live call to MATCHBox prior to parsing and filtering.\n')
            self.__raw_dump(self.api_data,filename)
            sys.exit()

    def __str__(self):
        return json.dumps(self.api_data,sort_keys=True,indent=4)

    def __api_call(self):
        # Call to API to retrienve data. Using cURL rather than requests since requests
        # takes bloody forever!
        curl_cmd = 'curl -u {}:{} -s "{}"'.format(
            self.creds['username'],self.creds['password'],self.url
        )
        request = os.popen(curl_cmd).read()
        return json.loads(request)
        
    @staticmethod
    def __raw_dump(data,filename=None):
        # Dump a raw, unprocessed matchbox for dev purposes.
        if not filename:
            filename = 'raw_mb_dump.json'
        with open(filename,'w') as fh:
            json.dump(data,fh)
