from driver.driver_manager import DriverManager

app_path = 'xxx'
package_name, activity_name = 'xxx', 'xxx'
# 初始化并上传app
mDriverManager = DriverManager('android', app_path)

# 1、获取任意一个可用设备
driver_info = mDriverManager.get_driver(package_name, activity_name)
# 2、获取指定标号的设备
driver_info = mDriverManager.get_driver(package_name, activity_name, serial_no='ca352a47')
# 3、获取所有可用设备
driver_info = mDriverManager.get_driver(package_name, activity_name, acquire_all_device=True)
print(driver_info)
# 获取driver对象
for serial_no in driver_info:
    driver = driver_info[serial_no]['driver']
# 释放设备
mDriverManager.close()
'''
driver_info示例
{
	'ca352a47': {
		'device_status': 'STF_LOCKED',
		'appium_hub': 'http://1.1.1.1:4727/wd/hub',
		'ssh_client':  < driver.ssh_manager.SSHClient object at 0x000001EAD52CA860 > ,
		'release': '9',
		'sdk': '28',
		'manufacturer': 'Xiaomi',
		'model': 'Redmi K20',
		'wm_size': '1080x2340',
		'driver':  < appium.webdriver.webdriver.WebDriver(session = "246646ac-bf0a-49a8-8b99-7a68b40a7444") >
	}
}
'''
