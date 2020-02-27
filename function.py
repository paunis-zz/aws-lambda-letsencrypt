#!/usr/bin/env python3

import boto3
import certbot.main
import OpenSSL.crypto
from OpenSSL import crypto
import os
import sys
import logging
import json
from datetime import datetime
from datetime import timedelta
import pytz
from botocore.exceptions import ClientError


def setup_logging():
    logger = logging.getLogger()
    for h in logger.handlers:
        logger.removeHandler(h)
    formatter = logging.Formatter(
        "[%(levelname)s] %(asctime)s, %(funcName)s, %(message)s", "%Y-%m-%d %H:%M:%S")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger = logging.getLogger(__name__)
    logger.addHandler(handler)
    logger.raiseException = True
    try:
        LOGLEVEL = os.environ.get('LOGLEVEL', 'DEBUG').upper()
        logger.basicConfig(level=LOGLEVEL)
    except:
        logger.setLevel(logging.INFO)
    return logger


LOGGER = setup_logging()


def read_and_delete_file(path):
    with open(path, 'r') as file:
        contents = file.read()
    os.remove(path)
    return contents


def provision_cert(email, domain, staging):
    certbot_parameters = [
        'certonly',                             # Obtain a cert but don't install it
        '-n',                                   # Run in non-interactive mode
        '--agree-tos',                          # Agree to the terms of service,
        '--email', email,                       # Email
        '--dns-route53',                        # Use dns challenge with route53
        '-d', domain,                           # Domains to provision certs for
        '--rsa-key-size', '4096',  # Key size
        '--config-dir', '/tmp/config-dir/',
        '--work-dir', '/tmp/work-dir/',
        '--logs-dir', '/tmp/logs-dir/',
    ]

    if staging == 'true':
        certbot_parameters.append('--staging')
        LOGGER.info('Using the Letsencrypt staging environment')

    LOGGER.info('Start provisioning certificate')
    certbot.main.main(certbot_parameters)

    path = f'/tmp/config-dir/live/{domain}/'
    data = {
        'certificate': read_and_delete_file(f'{path}cert.pem'),
        'private_key': read_and_delete_file(f'{path}privkey.pem'),
        'certificate_chain': read_and_delete_file(f'{path}chain.pem')
    }

    return data


def needs_renewal(secret_name):

    now = datetime.now(pytz.utc)
    client = boto3.client('secretsmanager')
    try:
        response = client.get_secret_value(
            SecretId=secret_name
        )
        creation_date = response['CreatedDate']
        expire_date = creation_date + timedelta(days=90)

        return (expire_date - now).days

    except ClientError as e:
        print(e.response)
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return -1


def create_secret(name, secret):
    cl = boto3.client('secretsmanager')
    LOGGER.info('Writing the new secret')
    cl.create_secret(
        Name=name,
        SecretString=secret
    )


def update_secret(name, secret):
    cl = boto3.client('secretsmanager')
    LOGGER.info('Update the secret')
    cl.update_secret(
        SecretId=name,
        SecretString=secret
    )


def lambda_handler(event, context):
    domain = os.environ['DOMAIN']
    email = os.environ['EMAIL']
    certificate_name = os.environ['CERTIFICATE_NAME']
    key_name = os.environ['KEY_NAME']
    staging = os.environ['CERTBOT_STAGING']

    message = needs_renewal(certificate_name)

    if message < 0:
        try:
            LOGGER.info('Create new certificate')
            cert = provision_cert(email, domain, staging)
            update_secret(
                key_name, cert['private_key'])
            update_secret(
                certificate_name, cert['certificate'])
        except Exception as e:
            print(e)
    elif message < 21:
        try:
            LOGGER.info('Update new certificate')
            cert = provision_cert(email, domain, staging)
            update_secret(
                key_name, cert['private_key'])
            update_secret(
                certificate_name, cert['certificate'])
        except Exception as e:
            print(e)
    else:
        LOGGER.info('Renewal not needed')
        LOGGER.info(message)
        pass
