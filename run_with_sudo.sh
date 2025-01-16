
cd /
cd home/moths


source venv/bin/activate

cd moths_lighting/
sudo -u moths git pull origin main

cd ..
sudo -E venv/bin/python moths_lighting/moths_lighting/main.py
