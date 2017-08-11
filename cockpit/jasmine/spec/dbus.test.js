const cockpit = require("cockpit");


function startRegister() {
    const service = cockpit.dbus("com.redhat.RHSM1", {"superuser": "require"});
    let proxy = service.proxy("com.redhat.RHSM1.RegisterServer", "/com/redhat/RHSM1/RegisterServer");
    let start = proxy.Start();

    function handler(result) {
        console.log(result);
        return result;
    }

    function err_handler(err) {
        console.log(err);
    }


  return start.then(handler)
    .then(sock => {
      console.log(sock);
    })
    .fail(err_handler);
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("DOMContentLoaded finished");
    startRegister();
})

/*
 * This is the actual test that, once the proxy.Start() issue is resolved will 
 * be how the integration tests are done
describe("Check that we can Register with subscription-manager", function() {

    it("Should create a unix socket when we register", function() {
        let sock = startRegister();
        expect(typeof sock == "string").toBe(true);
    });
});
*/
