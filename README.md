# About

Create / Renew Letsencrypt certificates and save them to AWS Secrets Manager

## Usage

Create virtual environment and download dependencies

```
$ make install
```

To create the zip files for uploading in AWS:

- run
```
$ make zip
```
This will create ''lambda_function.zip'' and ''lambda_layer.zip''
- upload the zip files to AWS
