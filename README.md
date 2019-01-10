# Ryuk

A simple HTTP server with upload file capabilities.

### Screenshot

![screenshot](img/screenshot.png)

### Requirements

- `python3+`

### Run the server

Run the server listening on port 8000 from terminal:
```
>> python RyukHTTPServer.py
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

To run via systemd:
```
cp ryuk.service ~/.config/systemd/user/
systemctl --user start ryuk
```

### Last words
> "For me, apples are like cigarettes and liquor for humans. If I'm deprived,
> I go into withdrawals." - Ryuk
