#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import time
from flask import Flask

app = Flask(__name__)


def hello1():
    return "Hello World!<br>This is powered by Python backend!2"

@app.route("/")
def hello2():
    return "Hello World!<br>This is powered by Python backend!2aa"

if __name__ == "__main__":
    print('on hello2')
    app.run(host="127.0.0.1", port=5000)
