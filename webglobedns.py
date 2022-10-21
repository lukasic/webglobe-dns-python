#! -*- coding: utf-8 -*-

import requests
import json

jp = lambda x: print(json.dumps(x, indent=2))

api_url = "https://api.webglobe.com"
api_username = None
api_password = None


class ResultSet:
    def __init__(self, data):
        assert type(data) in (list, set)
        if len(data) > 0:
            t = type(data[0])
            for i in data:
                assert type(i) == t
        self.data = list(data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, position):
        return self.data[position]

    def get(self, *args, **kwargs):
        if len(args) == 1:
            kwargs['id'] = args[0]
        
        assert len(kwargs) > 0

        filtered = self.filter(**kwargs)
        assert len(filtered) == 1
        return filtered[0]

    def filter(self, **kwargs):
        #assert len(kwargs) > 0
        filtered = self.data
        for k,v in kwargs.items():
            f = lambda x: getattr(x, k) == v
            filtered = list(filter(f, filtered))
        return ResultSet(filtered)

    def sort(self, key="id"):
        s = list(self.data)
        s.sort(key=lambda x: getattr(x, key))
        return ResultSet(s)

    def count(self):
        return len(self.data)

    def all(self):
        return self


class WebglobeDnsRecord:
    def __init__(self, zone, id=None, lazy=True):
        assert type(zone) == WebglobeDnsZone    
        self.zone = zone
        self.id = id
        self._aux = None
        self._type = None
        self._data = None
        self.__locked = {}

        if not lazy:
            self._load()

    def _load(self):
        raise AssertionError("Not implemented yet.")

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, val):
        self._type = val.upper()

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, val):
        if self.type == "MX":
            if not val.endswith("."):
                raise ValueError("MX record data must be in FQDN format and end with dot.")
        self._data = val

    @property
    def aux(self):
        return self._aux

    @aux.setter
    def aux(self, val):
        if self.type != "MX":
            raise AttributeError("WebglobeDnsRecord type -> %s does not have attribute 'aux'." % self.type)
        self._aux = int(val)

    def create(self):
        assert not self.id
        self.validate()

        url = "/{domain_id}/dns".format(
            domain_id=self.zone.id)

        r = self.zone.api._post(url, self.__export())
        self.id = r.json()['data']['id']
        self.__lock()

    def validate(self):
        if self.type == "MX" and not self.aux:
            raise AssertionError("Missing priority for MX (attribute aux)")

    def save(self):
        if not self.ischanged():
            return

        if not self.id:
            return self.create()

        self.validate()

        url = "/{domain_id}/dns/{record_id}".format(
            domain_id=self.zone.id,
            record_id=self.id)
        r = self.zone.api._put(url, self.__export())
        self.__lock()

    def delete(self):
        assert self.id
        url = "/{domain_id}/dns/{record_id}".format(
            domain_id=self.zone.id,
            record_id=self.id)
        r = self.zone.api._delete(url, self.__export())
        self.id = None
        self.__locked = {}

    def bindformat(self):
        if self.type != "MX":
            return "{name} {ttl} {type} {data}".format(**self.__export())
        else:
            return "{name} {ttl} {type} {aux} {data}".format(**self.__export())

    def __repr__(self):
        return "<WebglobeDnsRecord({id})".format(id=self.id)

        #return "<WebglobeDnsRecord({id} -> {type}/{name}>".format(
        #   id=self.id,
        #   type=self.type,
        #   name=self.name)

    def __export(self):
        obj = {
            'type': self.type,
            'name': self.name,
            'ttl': self.ttl,
            'data': self.data
        }
        if self.type == "MX":
            obj['aux'] = self.aux
        return obj

    def __lock(self):
        self.__locked = self.__export()

    def ischanged(self):
        return self.__locked != self.__export()


    @staticmethod
    def from_json(zone, data):
        r = WebglobeDnsRecord(zone, data['id'], lazy=True)
        r.type = data['type']
        r.name = data['name']
        # override setter for MX type:
        #   existing zone can contain records in non-fqdn format
        if r.type == "MX":
            r._data = data['data']
        else:
            r.data = data['data']
        r.ttl = data['ttl']
        if r.type == "MX":
            r.aux = data['aux']
        r.__lock()
        return r


class WebglobeDnsZone:
    def __init__(self, api, id, lazy=False):
        assert type(api) == WebglobeDnsApi

        self.api = api
        self.id = int(id)

        if not lazy:
            self._load()

    def _load(self):
        raise AssertionError("Not implemented yet.")

    @property
    def records(self):
        url = "/{}/dns".format(self.id)
        return ResultSet([
            WebglobeDnsRecord.from_json(self, r)
            for r in self.api._get(url).json()['data']['records'] ])

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<WebglobeDnsZone({id}) -> {name}>".format(
            id=self.id,
            name=self.name)

    @staticmethod
    def from_json(api, data):
        d = WebglobeDnsZone(api, data['domain_id'], lazy=True)
        d.name = data['domain']
        return d


class WebglobeDnsApiException(Exception):
    def __init__(self, error):
        self.code = error['code']
        self.message = error['message']
        super(Exception, self).__init__(error['message'])

class DuplicateRecordException(WebglobeDnsApiException):
    def __init__(self, error):
        return super(WebglobeDnsApiException, self).__init__(error)

def raise_on_err(response):
    if response.status_code != 200:
        error = response.json()['error']
        error_code = error['code']

        if error_code == 937:
            raise DuplicateRecordException(error)

        raise WebglobeDnsApiException(error)

class WebglobeDnsApi:
    def __init__(self, api_url):
        self.api_url = api_url
        self.token = None
        self.headers = None

    def login(self, username, password, otp=None, sms_code=None):
        login_data = {
            "login": username,
            "password": password
            }
        if otp:
            login_data["otp"] = otp
        if sms_code:
            login_data["sms"] = sms_code

        r = requests.post(
                self.api_url + "/auth/login",
                json=login_data)
        if r.status_code != 200:
            raise WebglobeDnsApiException(r.json()['error'])
        self.token = r.json()['data']['token']
        
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(self.token)
        }

    def _get(self, url):
        r = requests.get(
            self.api_url + url,
            headers=self.headers)
        raise_on_err(r)
        return r

    def _put(self, url, data):
        r = requests.put(
            self.api_url + url,
            headers=self.headers,
            json=data)
        raise_on_err(r)
        return r

    def _post(self, url, data):
        r = requests.post(
            self.api_url + url,
            headers=self.headers,
            json=data)
        raise_on_err(r)
        return r

    def _delete(self, url, data):
        r = requests.delete(
            self.api_url + url,
            headers=self.headers)
        raise_on_err(r)
        return r

    @property
    def zones(self):
        r = self._get("/domains?full=true").json()
        domains = r['domains']['reg_domains']

        return ResultSet([
            WebglobeDnsZone.from_json(self, d)
            for d in domains['data']
            if d['status'] == "hotovo" ])

