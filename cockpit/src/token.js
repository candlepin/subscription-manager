var status;
var xhttp = new XMLHttpRequest();
// var host = window.location.hostname;
var host = 'localhost';
// xhttp.open('GET', "https://localhost:8443/candlepin/status", true);
// xhttp.onreadystatechange = function() {
//     var realm;
//     var authUrl;
//     var clientId;
//
//     if (xhttp.readyState == 4) {
//         if (xhttp.status == 200) {
//             var status = JSON.parse(xhttp.responseText);
//             realm = status['realm']
//             authUrl = status['authUrl']
//             clientId = status['resource']
//             console.log(realm);
//         }
        var keycloak = Keycloak({
            url: 'https://sso.dev1.redhat.com/auth',
            realm: 'redhat-external',
            clientId: "candlepin-test"
        });
        keycloak.init({checkLoginIframe: false}).success(function(authenticated) {

            if (!authenticated) {
                keycloak.login();
            }
            else {
                document.getElementById("printToken").innerHTML = keycloak.refreshToken;
                document.cookie = "Keycloak_Token=Authorization: Bearer "+keycloak.token;
            }
        }).error(function() {
            alert('failed to initialize');
        });

    // else {
    //     console.log("Error", xhttp.statusText);
    // }
//};
// xhttp.send();
