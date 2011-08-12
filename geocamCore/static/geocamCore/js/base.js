function set_cookie(name,value,days) {
    var expires = "";
    
    if (days) {
        var date = new Date();
        date.setTime(date.getTime()+(days*24*60*60*1000));
        var expires = "; expires="+date.toGMTString();
    }

    return (document.cookie = name+"="+value+expires+"; path=/");
}

function get_cookie(name) {
    var start = document.cookie.indexOf( name + "=" );
    var len = start + name.length + 1;
    
    if((!start) && (name != document.cookie.substring(0, name.length))) {
        return null;
    }
    
    if(start == -1) { return null; }
    
    var end = document.cookie.indexOf( ";", len );
    if(end == -1) end = document.cookie.length;
    
    return unescape(document.cookie.substring(len, end));
}

function remember_datum(key, value) {
    set_cookie(key, value);
}

function get_datum(key) {
    return get_cookie(key);
}

function swapClass(obj, a, b) {
    $(obj).removeClass(a);
    $(obj).addClass(b);
}

function go_to_view(url) {
    window.location.href = url;
}

function toggle_night_mode() {
    var body = document.body;
    
    if($(body).hasClass('daytime')) {
        swapClass(body, 'daytime', 'nighttime');
        remember_datum('mode', 'nighttime');
    }
    else {
        swapClass(body, 'nighttime', 'daytime');
        remember_datum('mode', 'daytime');
    }
    
    if(typeof(geocamAware) != "undefined") {
        geocamAware.toggleMapType();
    }
}

function toggle_menu() {
    // console.log("Hello!");
    $('#direction').toggleClass('menu_close');
    $('#pop_up_menu_list').slideToggle('slow');

    if($('#direction').hasClass('menu_close')) {
        $('#direction').text('Close Menu');
    }
    else {
        $('#direction').text('Open Menu');
    }
}

function replaceAll(txt, replace, with_this) {
  return txt.replace(new RegExp(replace, 'g'),with_this);
}