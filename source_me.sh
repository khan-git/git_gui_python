
dest="gitgui_venv"

echo "Check python environment"
if [ ! -d "$(pwd)/gitgui_venv" ]
then
    if [[ -d "${dest}" ]]
    then
        echo "WARNING: ${dest} already exits! Delete this enviroment before running this script again, 'rm -rf ${dest}'."
        return
    fi

    if [ ! -e "requirements.txt" ]
    then
        echo "ERROR: Missing requirements.txt"
        return
    fi

    python3 -m venv ${dest}
    if [ "$?" -ne 0 ]
    then
        echo "ERROR: Venv failed"
        return
    fi

    source ${dest}/bin/activate
    python -V

    pip install -r requirements.txt
    if [ "$?" -ne 0 ]
    then
        echo "ERROR: pip install failed"
        return
    fi

    echo "Venv ${dest} created!"
    echo -e "\n\nTo enter the new virtual enviroment enter: 'source ${dest}/bin/activate'\n\n"
    echo -e "\n\nTo leave the new virtual enviroment just enter: 'deactivate'\n\n"
fi

source gitgui_venv/bin/activate
python -V

export PATH=$(pwd)/bin:$PATH
