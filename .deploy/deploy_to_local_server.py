from decouple import ConfigParser, config
from tqdm import tqdm
import paramiko
import yaml
import os


def send_files_via_ssh(
    host, port, username, password, local_paths, remote_path, command_to_execute
):
    """
    Sends specified files and/or folders through SSH and executes a command.

    Args:
        host (str): Hostname or IP address of the SSH server.
        port (int): Port number of the SSH server (usually 22).
        username (str): Username for SSH authentication.
        password (str): Password for SSH authentication.
        local_paths (list): List of local file/folder paths to send.
        remote_path (str): Path on the remote server to store files.
        command_to_execute (str): Command to execute on the remote server.

    Returns:
        bool: True if files were sent and command executed successfully, False otherwise.
    """
    try:
        # Connect to SSH server
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
        )

        # Create SFTP client
        sftp = ssh_client.open_sftp()

        # Upload files/folders
        for local_path in tqdm(local_paths):
            # print(f"Looking at the {local_path=}")
            if os.path.isfile(local_path):
                # Replace existing files and create if non-existing
                filename = os.path.basename(local_path)
                remote_file_path = f"{remote_path}/{filename}".replace(
                    "\\", "/"
                )  # Replace backslashes with forward slashes
                # print(f"{filename=} will be saved on {remote_file_path=}")
                sftp.put(local_path, remote_file_path)
            elif os.path.isdir(local_path):
                # Replace existing folders and create if non-existing
                local_basename = os.path.basename(local_path)
                remote_dir = f"{remote_path}/{local_basename}".replace(
                    "\\", "/"
                )  # Replace backslashes with forward slashes
                try:
                    sftp.stat(remote_dir)
                except FileNotFoundError:
                    sftp.mkdir(
                        remote_dir, mode=0o755
                    )  # Create directory with permissions 755
                # print(f"{local_basename=} will be saved on {remote_dir=}")
                for root, dirs, files in os.walk(local_path):
                    root = root.replace("\\", "/")
                    relative_root = root.replace(local_path, "").lstrip("/")
                    for dir_name in dirs:
                        remote_dir_path = (
                            f"{remote_dir}/{relative_root}/{dir_name}".replace(
                                "\\", "/"
                            )
                        )
                        try:
                            sftp.stat(remote_dir_path)
                        except FileNotFoundError:
                            sftp.mkdir(remote_dir_path, mode=0o755)
                    for file in files:
                        local_file_path = os.path.join(root, file)
                        remote_file_path = (
                            f"{remote_dir}/{relative_root}/{file}".replace("\\", "/")
                        )
                        sftp.put(local_file_path, remote_file_path)

        # Execute command
        stdin, stdout, stderr = ssh_client.exec_command(command_to_execute)
        # You can optionally print the output of the command
        print("Command output:")
        for line in stdout:
            print(line.strip())
        print(f"{stdin=} {stderr=}")

        # Close SFTP session and SSH connection
        sftp.close()
        ssh_client.close()

        print("Files sent and command executed successfully.")
        return True

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False


def load_file_paths_from_yaml(yaml_file):
    """
    Load file paths from a YAML file.

    Args:
        yaml_file (str): Path to the YAML file.

    Returns:
        list: List of file paths.
    """
    with open(yaml_file, "r") as file:
        data = yaml.safe_load(file)
        return data["files"]


if __name__ == "__main__":

    # Get environment variables
    host = config("SSH_HOST")
    port = int(config("SSH_PORT"))
    username = config("SSH_USERNAME")
    password = config("SSH_PASSWORD")
    remote_path = config("REMOTE_PATH")
    yaml_file = "tracker.yaml"
    remote_pyc_files = "rm ./*/*.pyc"
    command_to_execute = (
        f"cd {remote_path};{remote_pyc_files};sh docker-generate-image.sh"
    )

    # Load file paths from YAML
    local_paths = load_file_paths_from_yaml(yaml_file)

    # Call the function to send files via SSH and execute a command
    send_files_via_ssh(
        host, port, username, password, local_paths, remote_path, command_to_execute
    )
