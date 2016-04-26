import dbus
import rhsmlib.dbus.private.register_service as service


if __name__ == '__main__':
    client = dbus.connection.Connection("unix:path=/tmp/subman.sock")
    proxy = client.get_object(service.DBUS_NAME, service.DBUS_PATH)
    obj = dbus.Interface(proxy, service.DBUS_NAME)
    print(obj.reverse("hello"))
