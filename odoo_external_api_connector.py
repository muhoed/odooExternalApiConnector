import xmlrpc.client as xc
import re


# Implementation of access to Odoo server external API. Oficial documentation:
# https://www.odoo.com/documentation/14.0/developer/misc/api/odoo.html
# Dmitry Argunov aka muhoed, dargunov@yahoo.com
# version 0.1

class odooExternalApiConnector:
    """
    Helper class to create connection to Odoo ERP server through its external API
    using xmlprc.client. The following methods are implemented:
    class odooExternalApiConnector
    Parameters:     - url (optional[str]) - full url path to Odoo server ('https://odoo.server.com/). 
                    Default to None.
                    - host (optional[str]) - path to Odoo server as 'hostname:port'.
                    Default to 'localhost:8069'.
                    - db (optional[str]) - name of database. First database existing on the server
                    and accessed with the credentials given will be connected if the parameter is not 
                    provided. Default to None.
                    - username (optional[str]) - username for authentication on the Odoo server.
                    Default to None.
                    - password (optional[str]) - password for authentication on the Odoo server.
                    Default to None.
    Methods (see detailed information in the description of the respective method):
    odooExternalApiConnector.get_ids(
        self, model_name=None, filter=[], offset=None, limit=None
        ) -> dict
    odooExternalApiConnector.get_records(
        self, model_name=None, filter=[], offset=None, limit=None, fields=[]
        ) -> dict
    odooExternalApiConnector.get_count(
        self, model_name=None, filter=[], offset=None, limit=None
        ) -> dict
    odooExternalApiConnector.get_fields(
        self, model_name=None, attributes=['string', 'help', 'type']
        ) -> dict
    odooExternalApiConnector.create_record(
        self, model_name=None, fields={}
        ) -> dict
    odooExternalApiConnector.update_record(
        self, model_name=None, ids=[], fields={}
        ) -> dict
    odooExternalApiConnector.delete_record(
        self, model_name=None, ids=[]
        ) -> dict
    odooExternalApiConnector.create_model(
        self, model_name=None, fields=[dict]
        ) -> dict
    All methods return a dictionary in a form {
        'error': 'error message'|None,
        <key1>: <value>|None|0,
        ...
        }.
    """
    def __init__(self, url=None, host=None, db=None, username=None, password=None) -> None:
        #full url path to odoo server instance as String
        self.url = url
        #'[hostname]:[port]' alternative to url
        self.host = "localhost:8069"
        if host:
            self.host = host
        #name of Odoo database as String
        self.db = db
        #username as String
        self.username = username
        #password as String
        self.password = password
        #uid of created connection
        self.uid = None

    def _get_host(self) -> str:
        """
        Returns host url of Odoo server.
        """
        return self.url if self.url else self.host

    def _create_connection(self) -> dict:
        """
        Creates a proxy connector to an Odoo server. Returns error if connection attempt
        was unsuccessful. Returns connection object and the server version information
        if succeed.
        """
        try:
            conn = xc.ServerProxy('{}/xmlrpc/2/common'.format(self._get_host()))
            ver = conn.version()
        except:
            return {"error": "Can't connect to Odoo server.", "conn": None, "version": None}
        return {"error": None, "conn": conn, "version": ver}

    def _get_db_name(self) -> list:
        """
        Returns a list of names of databases existing on the Odoo server.
        """
        db_serv_url = '{}/xmlrpc/db'.format(self._get_host())
        sock = xc.ServerProxy(db_serv_url)
        return sock.list()
        
    def _authenticate(self) -> dict:
        """Authenticates on the Odoo server database. Uses database name provided
        or connects to the first database found on the server accepting provided
        credentials. Sets UID value. Returns connected database and error if any.
        """
        connected_db = None
        connection = self._create_connection()
        error = connection["error"]
        if error is None:
            conn = connection["conn"]
            if self.db:
                try:
                    self.uid = conn.authenticate(self.db, self.username, self.password, {})
                    connected_db = self.db
                except:
                    error = "Can't connect to the database using credentials provided."
            else:
                dbs = self._get_db_name()
                if dbs != []:
                    for db in dbs:
                        try:
                            self.uid = conn.authenticate(db, self.username, self.password, {})
                            error = None
                            connected_db = db
                            break
                        except:
                            error = "Can't connect to the database using credentials provided."
                            continue
                else:
                    error = "No database exists on the server."
        
        if error:
            return {"error": error, "db": connected_db}
        
        return {"error": None, "db": connected_db}

    def _check_model_access(self, model_name:str, access_scope=['read']) -> dict:
        """
        Checks if an access to requested model is granted to provided credentials
        and access scope.
        Returns a proxy to requested model, database name and error if any.
        """
        error = None
        model = None
        auth = self._authenticate()
        if auth["error"] is None:
            mod = xc.ServerProxy('{}/xmlrpc/2/object'.format(self._get_host()))
            for access_right in access_scope:
                try:
                    perm_check = mod.execute_kw(auth["db"], self.uid, self.password, model_name, 
                                                'check_access_rights', [access_right], 
                                                {'raise_exception': False})
                    if not perm_check:
                        error = "The model does not exist or you do not have a permission to '{}' it.".format(access_right)
                        break
                    else:
                        model = mod
                except:
                    error = "Username/password are not valid."
        else:
            error = auth["error"]
        return {"error": error, "model": model, "db": auth["db"]}

    def get_ids(self, model_name=None, filter=[], offset=0, limit=0) -> dict:
        """
        Returns dictionary with the list of active records ids for requested 
        model as the second element and error message as the first element 
        if any.
        Accepted parameters:
        - model_name:str - name of a model. Required.
        - filter:list[list] - Odoo's search domains as list of lists. 
          Default to empty list.
        - offset:int - number of a first record to be returned. 
          Default to the first existing record.
        - limit:int - max number of records to return. Default to all.
        """
        if model_name:
            cursor = self._check_model_access(model_name)
            if cursor["error"]:
                return {"error": cursor["error"], "ids": None}
            model = cursor["model"]
            try:
                ids = model.execute_kw(cursor["db"], self.uid, self.password,
                                        model_name, 'search', [filter], 
                                        {'offset': offset, 'limit': limit})
                return {"error": None, "ids": ids}
            except Exception as err:
                return {"error": repr(err), "ids": None}
        return {"error": "Model name is required.", "ids": None}
        
    def get_records(self, model_name=None, filter=[], offset=0, limit=0, fields=[]) -> dict:
        """
        Returns dictionary with the list of records for requested model as
        the second element and error message as the first element if any.
        Accepted parameters:
        - model_name:str - name of a model. Required.
        - filter:list[list] - Odoo's search domains as list of lists. 
          Default to empty list.
        - offset:int - number of a first record to be returned. 
          Default to the first existing record.
        - limit:int - max number of records to return. Default to all.
        - fields:list - a list of fields to be returned for a record. 
          Default to empty list.
        """
        if model_name:
            cursor = self._check_model_access(model_name)
            if cursor["error"]:
                return {"error": cursor["error"], "records": None}
            model = cursor["model"]
            criteria = {
                'offset': offset, 'limit': limit, 'fields': fields
                }  if fields != [] else {
                    'offset': offset, 'limit': limit
                    }
            try:
                records = model.execute_kw(cursor["db"], self.uid, self.password,
                                            model_name, 'search_read', [filter],
                                            criteria)
                return {"error": None, "records": records}
            except Exception as err:
                return {"error": repr(err), "records": None}
        return {"error": "Model name is required.", "records": None}

    def get_count(self, model_name=None, filter=[]) -> dict:
        """
        Returns a number of active records matching criterias given for requested 
        model as the second element and error message as the first element 
        if any.
        Accepted parameters:
        - model_name:str - name of a model. Required.
        - filter:list[list] - Odoo's search domains as list of lists. 
          Default to list containing empty list.
        - offset:int - number of a first record to be returned. 
          Default to the first existing record.
        - limit:int - max number of records to return. Default to all.
        """
        if model_name:
            cursor = self._check_model_access(model_name)
            if cursor["error"]:
                return {"error": cursor["error"], "count": None}
            model = cursor["model"]
            try:
                records_count = model.execute_kw(cursor["db"], self.uid, self.password,
                                        model_name, 'search_count', [filter])
                return {"error": None, "count": records_count}
            except Exception as err:
                return {"error": repr(err), "count": None}
        return {"error": "Model name is required.", "count": None}

    def get_fields(self, model_name=None, attributes=['string', 'help', 'type']) -> dict:
        """
        Returns a dictionary of fields with its specified attributes (as dict of dicts) 
        for requested model as the second element and error message as the first element 
        if any.
        Accepted parameters:
        - model_name:str - name of a model. Required.
        - attributes:list - a list of field's attribute to be retrieved. 
          Default to ['string', 'help', 'type'].
        """
        if model_name:
            cursor = self._check_model_access(model_name)
            if cursor["error"]:
                return {"error": cursor["error"], "fields": None}
            model = cursor["model"]
            try:
                fields = model.execute_kw(cursor["db"], self.uid, self.password,
                                        model_name, 'fields_get', [], 
                                        {'attributes': attributes})
                return {"error": None, "fields": fields}
            except Exception as err:
                return {"error": repr(err), "fields": None}
        return {"error": "Model name is required.", "fields": None}

    def create_record(self, model_name=None, fields={}) -> dict:
        """
        Creates a single new record of requested model using fields values provided
        as a dictionary of name-value pairs.
        For any field which has a default value and is not set through the mapping 
        argument, the default value will be used. Please read Odoo official 
        documentation about setting velues for different type of model fields. 
        Returns the new record database identifier as the second element and error 
        message, if any, as the first element of a dictionary.
        Accepted parameters:
        - model_name:str - name of a model. Required.
        - fields:dict - a dictionary of fields name - value pairs. 
          Default to {'name': 'New <lettercased model name>'}.
        """
        if model_name:
            cursor = self._check_model_access(model_name, ['read', 'create'])
            if cursor["error"]:
                return {"error": cursor["error"], "id": None}
            model = cursor["model"]
            if fields == []:
                name = model_name.split(".", 1)
                name = name[0].replace(".", "_")
                fields = [{'name': 'New {}'.format(name.capitalize())}]
            try:
                new_record_id = model.execute_kw(cursor["db"], self.uid, self.password,
                                        model_name, 'create', [fields])
                return {"error": None, "id": new_record_id}
            except Exception as err:
                return {"error": repr(err), "id": None}
        return {"error": "Model name is required.", "id": None}

    def update_record(self, model_name=None, ids=[], fields={}) -> dict:
        """
        Updates records of requested model using a list of records ids and 
        fields values provided as a dictionary of name-value pairs.
        Multiple records can be updated simultaneously, but they will all 
        get the same values for the fields being set. Update of computed 
        fileds is not supported. Please read Odoo official \documentation about 
        setting velues for different type of model fields. 
        Returns a list of updated records database identifiers as the second 
        element and error message, if any, as the first element of a dictionary.
        Accepted parameters:
        - model_name:str - name of a model. Required.
        - ids:list - a list of records database identifiers. Default to empty list.
        - fields:dict - a dictionary of fields name - value pairs. 
          Default to empty dictionary.
        """
        if model_name:
            cursor = self._check_model_access(model_name, ['read', 'write'])
            if cursor["error"]:
                return {"error": cursor["error"], "ids": None}
            model = cursor["model"]
            if ids == []:
                return {"error": "No records to update.", "ids": None}
            if fields == {}:
                return {"error": None, "ids": ids}
            try:
                model.execute_kw(cursor["db"], self.uid, self.password,
                                        model_name, 'write', [ids, fields])
                return {"error": None, "ids": ids}
            except Exception as err:
                return {"error": repr(err), "ids": None}
        return {"error": "Model name is required.", "ids": None}

    def delete_record(self, model_name=None, ids=[]) -> dict:
        """
        Deletes records of requested model from a provided a list of records ids.
        Records can be deleted in bulk. 
        Returns a number of deleted records as the second element and error message, 
        if any, as the first element of a dictionary.
        Accepted parameters:
        - model_name:str - name of a model. Required.
        - ids:list - a list of records database identifiers. Default to empty list.
        """
        if model_name:
            cursor = self._check_model_access(model_name, ['read', 'unlink'])
            if cursor["error"]:
                return {"error": cursor["error"], "count": 0}
            model = cursor["model"]
            if ids == []:
                return {"error": "No records to delete.", "count": 0}
            try:
                model.execute_kw(cursor["db"], self.uid, self.password,
                                        model_name, 'unlink', [ids])
                return {"error": None, "count": len(ids)}
            except Exception as err:
                return {"error": repr(err), "count": 0}
        return {"error": "Model name is required.", "count": 0}

    def create_model(self, model_name=None, fields=[]) -> dict:
        """
        Creates a new model. Returns the new model id:int as the second element 
        and error message, if any, as the first element of a dictionary.
        Please read Odoo official documentation about setting velues for 
        different type of model fields.
        It is not possible to add new methods to a custom model, only fields 
        Accepted parameters:
        - model_name:str - name of a model. Example: 'My Model' - model 'x_my_model'
          will be created. Required.
        - fields:list[dict] - a list of fields in a form of field's name-value 
          pairs dictionaries.
        If an error occures when creating fileds provided the model will not be created.
        Default field parameters:
        - 'state': 'manual' (required)
        - 'ttype': 'char'
        - 'name': 'x_<model_name.lower().replace(" ", "_")>_<field index in the list>'
        """
        if model_name:
            cursor = self._check_model_access('ir.model', ['read', 'create', 'unlink'])
            if cursor["error"]:
                return {"error": cursor["error"], "id": None}
            model = cursor["model"]
            x_name = model_name
            x_name = x_name.lower()
            x_name = x_name.replace(" ", "_")
            if not re.match('^(x_).+', x_name):
                x_name = "x_" + x_name
            if not isinstance(fields, list):
                return {"error": "Incorrect fields format. Should be a list of dictionaries.", "id": None}
            try:
                id = model.execute_kw(cursor["db"], self.uid, self.password, 
                                        'ir.model', 'create', [{
                                                        'name': model_name,
                                                        'model': x_name,
                                                        'state': 'manual',
                                                    }]
                                        )
            except Exception as err:
                return {"error": repr(err), "id": None}
            if not id:
                return {"error": "The model was not created.", "id": None}
            if fields != []:
                for i, field in enumerate(fields):
                    if not isinstance(field, dict):
                        model.execute_kw(cursor["db"], self.uid, self.password,
                                        'ir.model', 'unlink', [id])
                        return {
                            "error": "Wrong format of a field attributes. Should be dictionary of key-value pairs.", 
                            "id": None
                            }
                    tmp_field = {
                        'model_id': id, 
                        'state': 'manual', 
                        'ttype': 'char', 
                        'name': "{}_field_{}".format(x_name, i)
                        }
                    if 'name' in field.keys():
                        if not re.match('^(x_).+', field["name"]):
                            field["name"] = "x_" + field["name"]
                    tmp_field.update(field)
                    fields[i] = tmp_field
                try:
                    model.execute_kw(
                            cursor["db"], self.uid, self.password,
                            'ir.model.fields', 'create', fields
                            )
                except Exception as err:
                    model.execute_kw(cursor["db"], self.uid, self.password,
                                        'ir.model', 'unlink', [id])
                    return {"error": repr(err), "id": None}
            return {"error": None, "id": id}
        return {"error": "Model name is required.", "id": None}


    def delete_model(self, model_name=None) -> dict:
        """TODO"""
        pass


    def update_model(self, model_name=None, mode=None, fields=[]) -> dict:
        """
        TODO
        """
        pass
