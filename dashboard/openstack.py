import json
import requests
from collections import OrderedDict
from model.model import db

ipaddr = '192.168.56.111'
project_id = '4b17b59a760a49b19c62b8611e43034d'

class Use_openstack():

    stacknum = 0

    # 토큰 받아오기
    def gettoken(self):
        token_payload = {
            "auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "name": "admin",
                            "domain": {
                                "name": "Default"
                            },
                            "password": "0000"
                        }
                    }
                },
                "scope": {
                    "project": {
                        "id": f'{project_id}'
                    }
                }

            }
        }

        # Openstack keystone token 발급
        auth_res = requests.post(f'http://{ipaddr}/identity/v3/auth/tokens',
                                 headers={'Content-type': 'application/json'},
                                 data=json.dumps(token_payload))

        # 발급받은 token 출력
        admin_token = auth_res.headers["X-Subject-Token"]

        return admin_token

    # 사용가능한 볼륨 info api
    def volume_info(self):
        admin_token = self.gettoken()

        volume_info = requests.get(f"http://{ipaddr}/volume/v3/{project_id}/volumes",
                                    headers={'X-Auth-Token': admin_token}).json()

        return volume_info

    # OS::Nova::Server 템플릿 생성
    def create_server_temp(self, name, server):
        if server[0]=="temp":
            server_temp = json.load(server[1])
            server_temp["instance"]["properties"]["name"] = name
            return server_temp
        else:
            with open('heat/server.json') as s:
                server_temp = json.load(s)
                server_temp["instance"]["properties"]["name"] = name
                server_temp["instance"]["properties"]["networks"][0]["network"] = server[0]
                server_temp["instance"]["properties"]["image"] = server[1]
            cursor = db.cursor()
            sql = f'''INSERT INTO instance(name, image, network, temp) VALUES (%s, %s, %s, %s)'''
            val = (name, server[1], server[0], server_temp)
            cursor.execute(sql, val)

            return server_temp

    # OS::Cinder::VolumeAttachment 템플릿 생성
    def create_volumeAttachment_temp(self, volume):
        volume = list(map(int, volume))
        volume_info = self.volume_info()
        vol_format = OrderedDict()
        runcmd_format=OrderedDict()
        with open('heat/runcmd.json') as r:
            runcmd_temp = json.load(r)
        for i in range(len(volume)):
            with open('heat/volumeattachment.json') as f:
                vol_info = json.load(f)
                vol_info["properties"]["volume_id"] = volume_info["volumes"][volume[i] - 1]["id"]
                cursor=db.cursor()
                sql = f'''SELECT cmd
                            FROM volcmdpair
                            WHERE voluuid={vol_info["properties"]["volume_id"]}'''
                cursor.execute(sql)
                result=json.load(cursor.fetchall()[0])
                for j in range(result):
                    runcmd_temp["runcmd"].append(j)
                # attach 할 volume이 두 개 이상일 때 위치 조정 vdb -> vdc ... 순
                vol_info["properties"]["mountpoint"] = f'/dev/vd{chr(98 + i)}'
                vol_format[f"vol{i + 1}"] = vol_info
        runcmd_format["runcmd"].update(runcmd_temp)
        return vol_format, runcmd_format

    # OS::Nova::Flavor 템플릿 생성
    def create_flavor_temp(self, flavor):
        if flavor[0]=="temp":
            flavor_temp = json.load(flavor[1])
            return flavor_temp
        else:
            with open('heat/flavor.json') as f:
                flavor_temp = json.load(f)
                flavor_temp["flavor1"]["properties"]["vcpus"] = flavor[0]
                flavor_temp["flavor1"]["properties"]["ram"] = flavor[1]
                flavor_temp["flavor1"]["properties"]["disk"] = flavor[2]
            cursor = db.cursor()
            sql = f'''INSERT INTO flavor(vcpu, ram, disk, temp) VALUES (%s, %s, %s, %s)'''
            val = (int(flavor[0]), int(flavor[1]), int(flavor[2]), flavor_temp)
            cursor.execute(sql, val)
            return flavor_temp

    # OS::Heat::CloudConfig 템플릿 생성
    def create_cloudconfig_temp(self, user):
        if user[0]=="temp":
            cloudconfig_temp = json.load(user[1])
            return cloudconfig_temp
        else:
            with open('heat/cloudconfig.json') as c:
                cloudconfig_temp=json.load(c)
            with open('heat/user_info.json') as u:
                user_json = json.load(u)
                user_json["name"]=user[0]
                cloudconfig_temp["myconfig"]["properties"]["cloud_config"]["users"].append(user_json)
                statement =f'"list"{user[0]}:{user[1]}\n'
                cloudconfig_temp["myconfig"]["properties"]["cloud_config"]["chpasswd"].update(statement)
            return cloudconfig_temp

    # 템플릿 최종 병합
    def create_instance(self, server_temp, flavor_temp, config_temp, volume_temp, runcmd_temp):
        admin_token = self.gettoken()

        with open('heat/stack.json') as s:
            stack_temp = json.load(s)

        server_temp["instance"]["properties"]["flavor"]["get_resource"]= "flavor1"
        stack_temp["template"]["resources"].update(server_temp)


        stack_temp["template"]["resources"].update(flavor_temp)

        stack_temp["template"]["resources"].update(volume_temp)

        config_temp=config_temp["myconfig"]["properties"]["cloud_config"].update(runcmd_temp)

        stack_temp["template"]["resources"].update(config_temp)

        # stack 생성 요청
        user_res = requests.post(f"http://{ipaddr}/heat-api/v1/{project_id}/stacks",
                                 headers={'X-Auth-Token': admin_token},
                                 data=json.dumps(stack_temp))

        print(json.dumps(user_res.json(), indent="\t"))

        return user_res.status_code

