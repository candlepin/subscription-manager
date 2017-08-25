//@flow
import "../.,/base1/cockpit"

export function startRegister() {
    const service = cockpit.dbus("com.redhat.RHSM1", {"superuser": "require"});

    let proxy = service.proxy("com.redhat.RHSM1.RegisterServer", "/com/redhat/RHSM1/RegisterServer");
    let start = proxy.Start();
    start.state();

    function handler(result) {
        console.log(result);
        return result;
    }

    function err_handler(err) { 
        console.log(err);
    }
    return start.done(handler).fail(err_handler);
}
