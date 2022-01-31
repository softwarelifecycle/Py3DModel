import glob
import io
import os
import os.path
import subprocess
import threading
from pathlib import Path
from PIL import Image
import PySimpleGUI as sg
import RegisterCameras
import TriggerCameras
import UtilityFunctions

HOME = "/Data/Dropbox/Python/CommercialSites/3dlovedones/"
TRANSFER = "/Data/Dropbox/Python/CommercialSites/3dlovedones/transfer"

MCAST_GRP = '224.0.0.251'
MCAST_PORT = 5007


def make_window(theme, cameras):
    """"
    Create layout for main window!
    """

    sg.theme(sg.OFFICIAL_PYSIMPLEGUI_THEME)

    headings = ["Camera #", "Name"]

    # layout in columns
    main_tab_left_column = [
        [sg.Frame(layout=[
            [sg.Text("# of Cameras")],
            [sg.Spin([i for i in range(1, 100)], initial_value=9,
                     k='-CAMERACOUNT-', size=(10, 10))],
            [sg.Text("Server IP Address")],
            [sg.Input(key="-IPADDRESS-", size=(15, 2))],
            [sg.Text("Exposure Setting")],
            [sg.Input(key="-EXPOSURE-", size=(15, 2))],
            [sg.Text("Destination", font='Rasa 12')],
            [sg.Input(key='-DESTTEXT-', size=20, default_text='Select Folder...', expand_x=True),
             sg.FolderBrowse(key="-DESTINATION-", target='-DESTTEXT-')]],
            title="Settings", expand_x=True, pad=(10, 5))],
        [sg.Frame(layout=[
            [sg.Button('Update Camera Code', key="-UPDATECODE-",
                       font='Rasa 12', size=20)],
            [sg.Button('Register Cameras', key="-REGISTER-",
                       font='Rasa 12', size=20)],
            [sg.Button('ReStart  Cameras Service',
                       key="-RESTART-", font='Rasa 12', size=20)],
            [sg.Button('ReBoot  Cameras', key="-REBOOT-",
                       font='Rasa 12', size=20)],
            [sg.Button('Shut Down  Cameras', key="-SHUTDOWN-",
                       font='Rasa 12', size=20)],
            [sg.Button('Ping Cameras', key="-PING-", font='Rasa 12', size=20)],
            [sg.Button('Clean Transfer Folder',
                       key="-DELETETRANSFERFOLDER-", font='Rasa 12', size=20)],
            [sg.Button('Clean Destination Folder',
                       key="-DELETEDESTFOLDER-", font='Rasa 12', size=20)],
            [sg.Button('Take Pictures!', key="-SNAP-",
                       font='Rasa 12', size=20)],
            [sg.Button("Convert to DNG's", key="-CONVERTPICS-", font='Rasa 12', size=20)],
            [sg.Button('Re-Load Images', key="-RELOAD-",
                       font='Rasa 12', size=20)],
            [sg.Button('Exit', font='Rasa 12', size=20)]], title="Actions", expand_x=True, pad=(10, 5))]]

    main_tab_right_column = [[sg.Table(values=cameras, headings=headings, max_col_width=25,
                                       # background_color='light blue',
                                       justification='right',
                                       num_rows=4,
                                       auto_size_columns=True,
                                       expand_x=True, expand_y=True,
                                       alternating_row_color='gray',
                                       key='-CAMERATABLE-',
                                       row_height=35,
                                       enable_events=True,
                                       tooltip='Camera Listing')],
                             [sg.Text(text="Status:", font='Rasa 22  bold', justification="bottom"),
                              sg.Text(key='-STATUSTEXT-', font='Rasa 18 bold')]]

    picture_column = [[sg.Frame(layout=[
        [sg.Image(key="-CAMERAIMAGE-")], [sg.Button('Re-Take Picture', key='-RETAKE-', font='Rasa 12', size=20)]],
        title="Camera Image", pad=(0, 0), size=(1000, 1000))]]

    tab_layout = [[sg.Col(main_tab_left_column, vertical_alignment='top', pad=(0, 0)),
                   sg.Col(main_tab_right_column, vertical_alignment='top',
                          expand_x=True, expand_y=True),
                   sg.Col(picture_column, vertical_alignment='top', expand_y=True, expand_x=True, pad=(0, 0),
                          size=(1000, 1000))]]

    theme_layout = [[sg.Text("See how elements look under different themes by choosing a different theme here!")],
                    [sg.Listbox(values=sg.theme_list(),
                                size=(20, 12),
                                key='-THEME LISTBOX-',
                                enable_events=True)],
                    [sg.Button("Set Theme")]]

    layout = [[sg.Text('3D Model Generator', font='Rasa 40', justification='center', expand_x=True,
                       relief="raised")]]

    layout += [[sg.TabGroup([[sg.Tab('Main', tab_layout), sg.Tab('Theme', theme_layout)]], key='-TAB GROUP-',
                            size=(1990, 790))]]
    return sg.Window('3D Loved Ones', layout, size=(1600, 900), location=(100, 100), resizable=True, finalize=True)


def updatecode(window, cameras):
    """
    Copy the OnCamera.py file to the registered cameras
    """

    for camera in cameras:
        camera_ip = camera[1]
        print(f'Updating Camera {camera_ip} with new code!')
        window['-STATUSTEXT-'].update(f'Transferring  for {camera_ip} .')
        copyCameraCode = subprocess.Popen(
            ["scp", f'{HOME}OnCamera.py', f'pi@{camera_ip}:/home/pi/listener/'])
        returncode = copyCameraCode.wait()

        if returncode != 0:
            sg.popup_error(f"Transfer did not complete for  {camera_ip}!")

    window['-STATUSTEXT-'].update(f'Restarting Services!.')


def snap(destination_path, window, max_cameras, cameras, cameraip='', exposure=90, ):
    """
    Send the SNAP command to the camera's to take a pic and then upload.
    """
    # clean up transfer folder first!
    cleanfolder(TRANSFER)
    window['-STATUSTEXT-'].update('Starting to take pictures...')
    print(f'CameraIP in Snap:{cameraip}')
    if len(cameraip) == 0:
        cameras.clear()
    window['-CAMERATABLE-'].update(cameras)

    if len(destination_path.strip()) == 0:
        sg.popup('Supply File Destination!', location=(800, 500))
    else:
        thread = threading.Thread(target=TriggerCameras.snap,
                                  args=(MCAST_GRP, MCAST_PORT, window, max_cameras, cameraip, exposure),
                                  daemon=True)
        thread.start()


def cleanfolder(path):
    """
    cleanup transfer directory either via menu option or when pics are taken.
    """
    trail = os.path.join(path, '')
    for f in glob.glob(f"{trail}*.*"):
        os.remove(f)


def reloadpics(path, window, cameras):
    clear_cameras("Re-Loading!", window, cameras)
    trail = os.path.join(path, '')
    print(f"dest path: {trail}")
    camera = 1
    for jpg in glob.glob(f"{trail}*.jpg"):
        print(f"jpg: {jpg}")
        cameras.append([camera, os.path.basename(jpg)])
        camera += 1

    sorted_cameras = sorted(cameras, key=lambda camera: camera[1])
    return sorted_cameras


def clear_cameras(message, window, cameras):
    window['-STATUSTEXT-'].update(message)
    cameras.clear()
    window['-CAMERATABLE-'].update(cameras)


def ping(MCAST_GRP, MCAST_PORT, window, max_cameras, cameras):
    clear_cameras("Pinging Cameras!", window, cameras)
    thread = threading.Thread(target=TriggerCameras.ping,
                              args=(MCAST_GRP, MCAST_PORT,
                                    max_cameras, window),
                              daemon=True)
    thread.start()


def main():
    """
    Entry point for creating view
    """

    cameras = [[0, "", ""]]

    window = make_window(sg.theme("Light Blue 2"), cameras)
    SERVER_IP = UtilityFunctions.get_ip_address()
    window['-IPADDRESS-'].update(SERVER_IP)
    window['-EXPOSURE-'].update(120)
    window['-STATUSTEXT-'].update("Waiting...")

    # This is an Event Loop
    while True:
        event, values = window.read()
        # keep an animation running so show things are happening
        # window['-GIF-IMAGE-'].update_animation(sg.DEFAULT_BASE64_LOADING_GIF, time_between_frames=100)
        if event not in (sg.TIMEOUT_EVENT, sg.WIN_CLOSED):
            print('============ Event = ', event, ' ==============')
            print('-------- Values Dictionary (key=value) --------')
            for key in values:
                print(key, ' = ', values[key])
        if event in (None, 'Exit'):
            print("[LOG] Clicked Exit!")
            ok_to_leave = sg.popup_yes_no("Do you really want to leave? Really?", title="Exit?", keep_on_top=True,
                                          location=(800, 500), grab_anywhere=True)
            if ok_to_leave == "Yes":
                break
        elif event == 'About':
            sg.popup('PySimpleGUI Demo All Elements',
                     'Right click anywhere to see right click menu',
                     'Visit each of the tabs to see available elements',
                     'Output of event and values can be see in Output tab',
                     'The event and values dictionary is printed after every event')
        elif event == "Set Theme":
            theme_chosen = values['-THEME LISTBOX-'][0]
            window.close()
            window = make_window(theme_chosen, cameras)

        elif event == "-UPDATECODE-":
            updatecode(window, cameras)

        elif event == "-RELOAD-":
            cameras = reloadpics(values['-DESTINATION-'], window, cameras)
            window['-CAMERATABLE-'].update(cameras)

        elif event == "-RESTART-":
            clear_cameras("ReStarting  Camera Service!", window, cameras)
            TriggerCameras.restartcameras(MCAST_GRP, MCAST_PORT)

        elif event == "-REBOOT-":
            clear_cameras("Starting to Reboot Cameras!", window, cameras)
            TriggerCameras.rebootcameras(MCAST_GRP, MCAST_PORT)
            ping(MCAST_GRP, MCAST_PORT, window, int(values['-CAMERACOUNT-']), cameras)

        elif event == "-SHUTDOWN-":
            clear_cameras("Shutting Down Cameras!", window, cameras)
            TriggerCameras.shutdowncameras(MCAST_GRP, MCAST_PORT)

        elif event == "-SNAP-":
            snap(values['-DESTINATION-'], window, int(values['-CAMERACOUNT-']), cameras, '',
                 int(values['-EXPOSURE-']), )

        elif event == "-RETAKE-":

            # selected row
            row = values["-CAMERATABLE-"][0]

            # then get that row from the cameras collection and grab the 2nd column for the camera IP!
            cameraip = cameras[row][1]
            print(f'Camera IP: {cameraip}')
            snap(values['-DESTINATION-'], window, int(values['-CAMERACOUNT-']), cameras,
                 cameraip, int(values['-EXPOSURE-']))

        elif event == "-PICTURETAKEN-":
            # check to see if this was for a single pic or all
            print(f'Picture Parm2 {values["-PICTURETAKEN-"][2]}')

            just_single_pic = values['-PICTURETAKEN-'][3]

            # 4th parm is single_pic.. T/F
            if just_single_pic == False:
                window['-STATUSTEXT-'].update(
                    f'Just took {values["-PICTURETAKEN-"][0]} pictures out of {values["-CAMERACOUNT-"]}!')
                window['-CAMERATABLE-'].update(cameras)
            else:
                print("Just re-took pic!")
                window['-STATUSTEXT-'].update(
                    f'Just re- took  picture for  {values["-PICTURETAKEN-"][2]}!')

            print(f"Just Single Pic = {just_single_pic}")
            source_file = f'{TRANSFER}/{os.path.basename(values["-PICTURETAKEN-"][2])}'
            # if exists(source_file):
            dest_file = f'{values["-DESTINATION-"]}/{os.path.basename(values["-PICTURETAKEN-"][2])}'
            file_name = UtilityFunctions.copyfiles(
                source_file, dest_file, just_single_pic)
            cameras.append([values["-PICTURETAKEN-"][0], file_name])
            cameras = sorted(cameras, 1)

            window['-STATUSTEXT-'].update(f'Just copied {file_name}! DONE!')

        elif event == '-DELETETRANSFERFOLDER-':
            cleanfolder(TRANSFER)

        elif event == "-DELETEDESTFOLDER-":
            cleanfolder(values['-DESTINATION-'])

        elif event == "-PING-":
            ping(MCAST_GRP, MCAST_PORT, window, int(values['-CAMERACOUNT-']), cameras)

        elif event == '-CAMERAPINGED-':
            cams = (int(values['-CAMERAPINGED-'][0]))
            window['-STATUSTEXT-'].update(f'Just pinged   {cams} cameras out of {values["-CAMERACOUNT-"]}!')
            cameras.append([cams, values["-CAMERAPINGED-"][1]])
            window['-CAMERATABLE-'].update(cameras)

        elif event == "-REGISTER-":
            clear_cameras("Registering Cameras!", window, cameras)
            thread = threading.Thread(target=RegisterCameras.registercameras,
                                      args=(
                                          int(values['-CAMERACOUNT-']), window),
                                      daemon=True)
            thread.start()
        elif event == "-CONVERTPICS-":
            UtilityFunctions.convertpics(values['-DESTINATION-'])

        elif event == '-CAMERAREGISTERED-':
            window['-STATUSTEXT-'].update(
                f'Just registered   {values["-CAMERAREGISTERED-"][0]} cameras out of {values["-CAMERACOUNT-"]}!')
            cameras.append([values["-CAMERAREGISTERED-"][0],
                            values["-CAMERAREGISTERED-"][1]])
            window['-CAMERATABLE-'].update(cameras)

        elif event == "-CAMERATABLE-":
            if (values["-CAMERATABLE-"]):
                row = values["-CAMERATABLE-"][0]

                # then get that row from the cameras collection and grab the 3rd column for the picture name!
                jpg = cameras[row][1]

                fullimagepath = f"{os.path.join(values['-DESTINATION-'], '')}{jpg}"
                path = Path(fullimagepath)
                if path.is_file():
                    image = Image.open(fullimagepath)
                    image.thumbnail((800, 800))
                    bio = io.BytesIO()
                    image.save(bio, format="PNG")
                    window["-CAMERAIMAGE-"].update(data=bio.getvalue())

    window.close()
    exit(0)


if __name__ == '__main__':
    main()
