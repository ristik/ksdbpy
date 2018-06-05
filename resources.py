from models import Token
from db import session

from gevent import monkey; monkey.patch_all()

from flask_restful import reqparse
from flask_restful import abort
from flask_restful import Resource
from flask import copy_current_request_context
from flask import make_response, copy_current_request_context
from werkzeug.exceptions import BadRequest, NotFound
from ksi import KSI, ksi_env
import settings
import hashlib
import binascii
import gevent

ksi = KSI(**ksi_env())

parser = reqparse.RequestParser()
parser.add_argument('task', type=str)
parser.add_argument('algorithm', type=str, default=settings.DEFAULT_HASHALG)
parser.add_argument('async', type=bool, default=False)

class HashVal():
    def __init__(self, v, a=None):
        self.v = binascii.unhexlify(v)
        if a is None:
            self.name = settings.DEFAULT_HASHALG
        else:
            self.name = a
        if self.name.lower() not in map(str.lower, hashlib.algorithms):
            raise BadRequest("Unknown hash algorithm: {} not in {}".format(self.name, hashlib.algorithms))

    def digest(self):
        return self.v


class KsdbResource(Resource):
    def get(self, hash_in):
        parsed_args = parser.parse_args()
        token = session.query(Token).filter(Token.hash == binascii.unhexlify(hash_in)).first()
        if not token:
            raise NotFound("Hash {} is not signed".format(hash_in))
        ksisig = ksi.parse(token.sig)
        result, code, reason = False, "", ""
        try:
            result, code, reason = ksi.verify_hash(ksisig, HashVal(hash_in, parsed_args['algorithm']))
        except Exception as e:
            abort(500, message="Signature verification error: " + str(e))
        if not result:
            abort(500, message="Invalid signature: " + reason)

        a, h = ksisig.get_data_hash()
        h = binascii.hexlify(h)
        pubdata = ksisig.get_publication_data()
        if pubdata is None:
            pubdata = "N/A"

        return {"alg": a,
                "hash": h,
                "signed_at": ksisig.get_signing_time_utc().strftime('%Y-%m-%dT%H:%M:%SZ'),
                "signed_by": ksisig.get_signer_id(),
                "result": code,
                "publication": pubdata}

    def put(self, hash_in):
        parsed_args = parser.parse_args()
        # print hash_in
        # print parsed_args
        token = session.query(Token).filter(Token.hash == binascii.unhexlify(hash_in)).first()
        if token:
            return 'Already signed', 200

        @copy_current_request_context
        def sign_stuff():
            # note: sign_hash() blocks gevent event loop for about a second.
            ksisig = ksi.sign_hash(HashVal(hash_in, parsed_args['algorithm']))
            token = Token(hash = binascii.unhexlify(hash_in), sig = ksisig.serialize(), by = 'myself')
            session.add(token)
            session.commit()

        if  parsed_args['async']:
            gevent.spawn(sign_stuff)
            return "Accepted", 202
        else:
            sign_stuff()
            return "Created", 201

class KsdbDlResource(Resource):
    def get(self, hash_in):
        parsed_args = parser.parse_args()
        token = session.query(Token).filter(Token.hash == binascii.unhexlify(hash_in)).first()
        if not token:
            raise NotFound("Hash {} is not signed".format(hash_in))
        ksisig = ksi.parse(token.sig)
        try:
            ksi.verify_hash(ksisig, HashVal(hash_in, parsed_args['algorithm']))
        except Exception as e:
            abort(500, message="Token verification error: " + str(e))

        response = make_response(token.sig)
        response.headers['Content-Type'] = 'application/octet-stream'
        response.headers['Content-Disposition'] = 'attachment; filename=signaturetoken.ksisig'
        response.headers['X-KSI-Signed-At'] = ksisig.get_signing_time_utc().strftime('%Y-%m-%dT%H:%M:%SZ')
        response.headers['X-KSI-Signed-By'] = ksisig.get_signer_id()
        return response
