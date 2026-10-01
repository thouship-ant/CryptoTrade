$(document).ready(function(){
	if ('serviceWorker' in navigator) {
	   // we are checking here to see if the browser supports the  service worker api
	window.addEventListener('load', function() {
		navigator.serviceWorker.register('../sw_delete.js').then(function(registration) {
		  // UnRegistration was successful
		  console.log('Service Worker unregistration was successful with scope: ', registration.scope);
		}, function(err) {
		  // registration failed :(
		  console.log('ServiceWorker unregistration failed: ', err);
		});
	  });
	}

});

