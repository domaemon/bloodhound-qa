#!/bin/bash
BHQA_PROJECT_DIR=`pwd`
cd $BHQA_PROJECT_DIR/installer
virtualenv bloodhound
source ./bloodhound/bin/activate
pip install -r requirements.txt
pip install ../bloodhound_search
python bloodhound_setup.py
cd $BHQA_PROJECT_DIR/testman4trac.1.5.2
./build.sh
tr-admin /home/msugano/GIT_DIR/bloodhound-qa/installer/bloodhound/environments/main upgrade
tr-admin /home/msugano/GIT_DIR/bloodhound-qa/installer/bloodhound/environments/main wiki upgrade

