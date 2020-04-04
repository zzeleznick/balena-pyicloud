set -e

cd "$(dirname ${BASH_SOURCE[0]})"

source ../env/bin/activate

source _env

# Ensure we can run python
python -c "import sys; print(sys.prefix)"
# Ensure we are in a virtualenv
python -c "import sys; print(sys.real_prefix)"

python ../src/main.py
