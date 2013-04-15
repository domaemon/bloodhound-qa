# project_path=$1

mkdir bin

cd tracgenericclass/0.10
python setup.py bdist_egg
cp dist/*.egg ../../bin

cd ../../tracgenericworkflow/0.10
python setup.py bdist_egg
cp dist/*.egg ../../bin

cd ../../sqlexecutor/0.10
python setup.py bdist_egg
cp dist/*.egg ../../bin

cd ../../testman4trac/0.10
python setup.py bdist_egg
cp dist/*.egg ../../bin

cd ../..

cp *.txt bin

cp bin/*.egg ../installer/bloodhound/environments/main/plugins/ 
