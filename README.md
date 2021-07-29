# odooExternalApiConnector
Implementation of access to Odoo server external API.
version 0.1

Helper class to create connection to Odoo ERP server through its external API using xmlprc.client. The following methods are implemented:

class odooExternalApiConnector

Parameters:     
- url (optional:str) - full url path to [Odoo server](https://odoo.server.com/). Default to None.
- host (optional:str) - path to Odoo server as 'hostname:port'. Default to 'localhost:8069'.
- db (optional:str) - name of database. First database existing on the server and accessed with the credentials given will be connected if the parameter is not provided. Default to None.
- username (optional:str) - username for authentication on the Odoo server. Default to None.
- password (optional:str) - password for authentication on the Odoo server. Default to None.
    
Methods (see detailed information in the description of the respective method):
    
.get_ids(self, model_name=None, filter=[], offset=None, limit=None) -> dict
    
.get_records(self, model_name=None, filter=[], offset=None, limit=None, fields=[]) -> dict
    
.get_count(self, model_name=None, filter=[], offset=None, limit=None) -> dict
    
.get_fields(self, model_name=None, attributes=['string', 'help', 'type']) -> dict
    
.create_record(self, model_name=None, fields={}) -> dict
    
.update_record(self, model_name=None, ids=[], fields={}) -> dict
    
.delete_record(self, model_name=None, ids=[]) -> dict
    
.create_model(self, model_name=None, fields=[dict]) -> dict
    
All methods return a dictionary in a form {'error': 'string|None', 'key1': 'value|None|0', ...}
