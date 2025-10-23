_r = None

def setup(redis_client):
    global _r
    _r = redis_client

def hget(key, field):
    value = _r.hget(key, field)
    if value is None:
        return None
    if field in ['home_id']:
        return int(value)
    return value

def hset(key, field=None, value=None, mapping=None):
    if mapping:
        _r.hset(key, mapping=mapping)
    else:
        _r.hset(key, field, value)
