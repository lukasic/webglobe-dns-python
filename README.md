# Webglobe DNS API Python Client

Simple python client for DNS records manipulation for zones hosted by https://www.webglobe.cz/.

**Alpha version. Do not use in production!**


## Example usage

```python

api_url = "https://api.webglobe.com"
api_username = "dns-subaccount@domain.tld"
api_password = "supersecretpassword"

try:

  w = WebglobeDnsApi(api_url)
  w.login(api_username, api_password)

  # list zones
  zones = w.zones.all()

  # get one zone
  zone = zones.get(name="domain.tld")
  # or
  zone = w.zones.get(name="domain.tld")

  # list all records
  records = zone.records.all()

  # filter only A records
  records = zone.records.filter(type="A")

  # filter only CNAME records with value "mx.domain.tld" and sort them
  records = zone.records.filter(type="MX", data="mx.domain.tld.").sort("data")

  # update records
  for r in records:
    r.ttl = 60
    r.data = "mx2.domain.tld"
    r.save()

  # delete records
  for r in records:
    if r.data startswith("mxbackup"):
      r.delete()

  # create new record

  r = WebglobeDnsRecord(zone)
  r.name = ""
  r.ttl = "60"
  r.type = "A"
  r.data = "10.0.2.8"
  r.save()
  
except WebglobeDnsApiException as e:
  print(e.message, e.code)


```
