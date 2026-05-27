#noi dung cua file mo ta
{
    "name": "Gym Management", #ten module
    "version": "1.0", #phien ban module
    "author": "vandat & hoangduy", #tac gia
    "description": "This module is used to manage gym members and equipment", #mo ta ngan gon ve module
    "website": "",
    "category": "General",
    "depends": ["base"], #danh sach cac module ma module nay phu thuoc

    "init_xml": [],

    "demo_xml": [   #cac file du lieu mau, duoc su dung de test module
        "data/demo.xml"
    ],

    "update_xml": [
        "data/cron.xml",
        "views/member_view.xml",
        "views/membership_view.xml",
        "views/package_view.xml",
        "views/checkin_view.xml",
        "views/trainer_view.xml",
        "views/gym_menu.xml",
    ],

    "active": False,
    "installable": True,
}