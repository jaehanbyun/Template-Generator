from model.model import db
from flask import Flask, render_template, request
from openstack import *

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report')
def report():
    envname = request.args.get('envname')
    net = request.args.get('net')
    os = request.args.get('os')
    user_name= request.args.get('user_name')

    flavor = []
    flavor.append(request.args.get('flavor_vcpu'))
    flavor.append(request.args.get('flavor_ram'))
    flavor.append(request.args.get('flavor_disk'))

    volume = []
    volume.append(request.args.get('env_volume'))
    volume.append(request.args.get('data_volume'))

    while None in volume:
        volume.remove(None)

    ob = Use_openstack()
    status = ob.create_instance(envname, net, os, user_name, flavor, volume)

    return render_template('report.html', envname=envname, status=status)

if __name__ == '__main__':
    app.run(debug=True)