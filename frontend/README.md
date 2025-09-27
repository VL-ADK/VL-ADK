# VL-ADK

This project was made for ShellHacks 2025.

Setup:

On your laptop:
- Tunnel the ports 8888, 8889, and 8890 to your Jetson Orin Nano.
*replace 2nd IP with your jetson local ip*
```
ssh -N -L 8888:127.0.0.1:8888 dvidal1205@10.108.169.202
ssh -N -L 8889:127.0.0.1:8889 dvidal1205@10.108.169.202
ssh -N -L 8890:127.0.0.1:8890 dvidal1205@10.108.169.202
```

Webapp:
- run ```npm install``` and ```npm run dev```
