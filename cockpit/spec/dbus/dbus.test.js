const cockpit = require("cockpit");
const service = cockpit.dbus("com.redhat.RHSM1", {"superuser": "require"});

describe("Check that we can Register with subscription-manager", function() {

    it("Should create a unix socket when we register", function() {
        let proxy = service.proxy("com.redhat.RHSM1.RegisterServer", "/com/redhat/RHSM1/RegisterServer");
        let start = proxy.Start();
        start.state();
    });
});
