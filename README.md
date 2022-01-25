# Server Manager

A robot in Lark to support password and SSH key management.

Use Docker to deploy, Redis to store data.

## Prepare

Deploy on root of master server, and master server can ssh to root of slave 
servers with SSH key `~/.ssh/id_rsa`. If server SSH port is not default 22, 
modify `~/.ssh/config` to add port information. Finally, root of master
server can `ssh SLAVE1` to all slave servers.

To use temporary password only, you should:
- Configure all controlled accounts in slave servers to have one day password
expiration, `chage -M 1 account`.
- Set permissions of `/usr/bin/passwd /usr/sbin/chpasswd` as 700.

## Environments

- `codes/.env` contains environments about lark communication and others. 
  - `APP_ID`
  - `APP_SECRET`
  - `VERIFICATION_TOKEN`
  - `ENCRYPT_KEY`
  - `LARK_HOST`  above all is used to communicate with lark.
  - `AUTH_KEY_TAG` used to add after SSH keys to recognize whether an SSH key 
    is added by this program.
- `codes/ENV/available_accounts` one line an account name that can be binded.
- `codes/ENV/available_servers` one line an server name. Note master server
  can SSH to all listed servers directly (double check when including self),
  and all servers have created accounts listed in `available_accounts`.

## Code structure

- `redis` saves redis config and redis dump file.
- `codes` saves all codes.
  - `api.py` communicates with Lark.
  - `command.py` parses commands and make action.
  - `db.py` communicates with db.
  - `decrypt.py` decrypts data from lark.
  - `event.py` deals with listened events.
  - `server.py` runs the server with Flask.
  - `ssh.py` send SSH commands to slave servers.
  - `utils.py` utility functions.

