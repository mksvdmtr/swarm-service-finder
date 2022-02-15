#!/usr/bin/env python

import os, json

projects_path = '/opt/containers/'
shell_script = 'start_services.sh'
raw_services_images = []
services_images = []
services_images_path = {}

ls_stream = os.popen('docker service ls --format "{{.Name}}={{.Image}}"')

ls_lines = ls_stream.readlines()

for nline in ls_lines:
    line = nline.strip()
    splited_line = line.split('=')
    raw_services_images.append(splited_line)

print('Inspecting docker services ...')

for service_image in raw_services_images:
    inspect_cmd = "docker service inspect " + service_image[0]
    inspect_stream = os.popen(inspect_cmd)
    inspect_out = inspect_stream.read()
    json_dict = json.loads(inspect_out)
    if not json_dict[0]['Spec']['Labels']:
      print('Warning: Labels is empty for service - %s\nSkip' % service_image[0])
      continue
    namespace = json_dict[0]['Spec']['Labels']['com.docker.stack.namespace']
    temp_list = []
    temp_list.append(namespace)
    temp_list.append(service_image[1])
    temp_list.append(service_image[0])
    services_images.append(temp_list)

script_file = open(shell_script, 'w')
conflicts_file = open('conflicts.log', 'w')
notfound_file = open('notfound.log', 'w')
script_file.write('#!/bin/bash\nset -e\n')

print('Searching docker-compose files ...')

for service_image in services_images:
    grep_cmd = "grep -l -R --include \*.yml --include \*.yaml " + service_image[1] + " " + projects_path + service_image[0] + " 2>/dev/null"
    grep_stream = os.popen(grep_cmd)
    grep_lines = grep_stream.readlines()
    if len(grep_lines) > 1:
        project_path = projects_path + service_image[0]
        print('Warning: detected more than one docker-compose with the same image: %s' % service_image[1])
        conflicts_file.write('Service: ' + service_image[2] + '\n')
        conflicts_file.write('Stack ' + service_image[0] + '\n')
        conflicts_file.write('Image: ' + service_image[1] + '\n')
        for grep_line in grep_lines:
            conflicts_file.write('Src: ' + grep_line.strip() + '\n')
        conflicts_file.write('\n\n')
        print('Service %s will be skipped\nsee the conflicts log: ./conflicts.log' % service_image[2])
        continue
    if len(grep_lines) == 1:
        script_line = "docker stack deploy --resolve-image=always --with-registry-auth --compose-file " + grep_lines[0].strip() + " " + service_image[0] + "\n"
        script_file.write(script_line)
        script_file.write('sleep 3\n')
    else:
      notfound_file.write('Stack: ' + service_image[0] + ' Service: ' + service_image[2] + ' Image: ' + service_image[1] + '\n')
script_file.close()
notfound_file.close()
conflicts_file.close()

st = os.stat(shell_script)
os.chmod(shell_script, st.st_mode | 0770)

print('%s shell script ready' % shell_script)
