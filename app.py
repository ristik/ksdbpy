#!/usr/bin/env python

from gevent import monkey; monkey.patch_all()

from flask import Flask
from flask_restful import Api
from gevent.pywsgi import WSGIServer


app = Flask(__name__)
api = Api(app)

from resources import KsdbResource, KsdbDlResource

api.add_resource(KsdbDlResource, '/ksdb/<string:hash_in>/download', endpoint='ksdbdl')
api.add_resource(KsdbResource, '/ksdb/<string:hash_in>', endpoint='ksdb')

if __name__ == '__main__':
    # app.run(host='0.0.0.0', debug=True)
    http_server = WSGIServer(('', 5000), app, spawn=32)
    http_server.serve_forever()

