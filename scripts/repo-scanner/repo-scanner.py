import os
import shutil
import sys
from venv import create
import yaml
import jinja2
import json
import semver

temp_dir = '/tmp/helm/'
template_file = 'profile-template.yaml.j2'

if sys.argv[1] == "download":
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.mkdir(temp_dir)
    stream = os.popen("helm search repo bitnami | awk '{ print $1 }'")
    output = stream.readlines()
    for chart in output:
        chart_name = chart.strip()
        os.system('helm pull {} --untar --untardir {}'.format(chart_name, temp_dir))
elif sys.argv[1] == "process":
    base_directory = os.path.dirname(os.path.abspath(__file__))
    charts_directory = '{}/../../charts'.format(base_directory)
    with open('{}/{}'.format(base_directory, template_file)) as file:
        template = jinja2.Template(file.read())
    directories = [ f.path for f in os.scandir(temp_dir) if f.is_dir() ]
    for directory in directories:
        with open('{}/Chart.yaml'.format(directory), "r") as stream:                
            chart_spec = yaml.safe_load(stream)       
            
        if os.path.exists('{}/{}'.format(charts_directory, chart_spec["name"])):
            create_directory = False
            should_render = False
            with open('{}/{}/Chart.yaml'.format(charts_directory, chart_spec["name"])) as existing_chart:
                chart = yaml.safe_load(existing_chart.read())
                current_profile_version = semver.VersionInfo.parse(chart["version"])
                current_dependency_version = semver.VersionInfo.parse(chart["dependencies"][0]["version"])
                latest_dependency_version = semver.VersionInfo.parse(chart_spec["version"])
                print('Existing version of profile {} is {} - current dep {}, latest dep {}'.format(chart_spec["name"], current_profile_version, current_dependency_version, latest_dependency_version))
                if current_dependency_version < latest_dependency_version:
                    should_render = True
                    new_profile_version = current_profile_version.bump_patch()
                    print("dependency out of date, new ver {}".format(new_profile_version))
        else:
            create_directory = True
            should_render = True
            new_profile_version = "0.0.1"

        if create_directory:
            os.mkdir('{}/{}'.format(charts_directory, chart_spec["name"]))
            open('{}/{}/values.yaml'.format(charts_directory, chart_spec["name"]), "a")

        if should_render:
            rendered_template = template.render(
                profile_name = chart_spec["name"],
                dependency_version = chart_spec["version"],
                dependency_repo = "https://charts.bitnami.com/bitnami",
                keywords = chart_spec["keywords"],
                category_name = chart_spec["annotations"]["category"],
                upstream_project = chart_spec["sources"][0],
                profile_version = new_profile_version
            )
            with open('{}/{}/Chart.yaml'.format(charts_directory, chart_spec["name"]), "w") as fh:
                fh.write(rendered_template)

            
            