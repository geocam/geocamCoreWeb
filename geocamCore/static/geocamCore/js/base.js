function set_cookie(name,value,days) {
    if (days) {
        var date = new Date();
        date.setTime(date.getTime()+(days*24*60*60*1000));
        var expires = "; expires="+date.toGMTString();
    }
    else var expires = "";
    return (document.cookie = name+"="+value+expires+"; path=/");
}

function remember_datum(key, value) {
    set_cookie(key, value);
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
}

function toggle_menu() {
    console.log("Hello!");
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