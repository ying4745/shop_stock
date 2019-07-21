var language = {
    "sProcessing": "处理中...",
    "sLengthMenu": "显示 _MENU_ 项结果",
    "sZeroRecords": "没有匹配结果",
    "sInfo": "显示第 _START_ 至 _END_ 项结果，共 _TOTAL_ 项",
    "sInfoEmpty": "显示第 0 至 0 项结果，共 0 项",
    "sInfoFiltered": "(由 _MAX_ 项结果过滤)",
    "sInfoPostFix": "",
    "sSearch": "搜索:",
    "sUrl": "",
    "sEmptyTable": "表中数据为空",
    "sLoadingRecords": "载入中...",
    "sInfoThousands": ",",
    "oPaginate": {
        "sFirst": "首页",
        "sPrevious": "上页",
        "sNext": "下页",
        "sLast": "末页"
    },
    "oAria": {
        "sSortAscending": ": 以升序排列此列",
        "sSortDescending": ": 以降序排列此列"
    }
};

// 四舍五入 转成两位小数
function getFloat2(x) {
    if (x !== '.') {
        var f = Math.round(x * 100) / 100;
        var s = f.toString();
        var rs = s.indexOf('.');
        if (rs <= 0) {
            rs = s.length;
            s += '.';
        }
        while (s.length <= rs + 2) {
            s += '0';
        }
        return s;
    } else {
        return '0.00';
    }
}

// 鼠标悬停 高亮行
$('#order_table').on('mouseover mouseout', 'tr', function (e) {
    if (e.type === 'mouseover') {
        $(this).addClass('highlight')
    } else {
        $(this).removeClass('highlight')
    }
});

// 鼠标悬浮显示大图 生成的html 需要on绑定父元素
$(".good-img-parent").on('mouseover mouseout', '.good_img', function (e) {
    var big_obj = $('<p id="big-image"><img width="500" height="500" src="' + $(this).attr('src') + '"></p>');
    // 旧元素 相对于左边 的偏移距离加元素的宽度
    var old_offleft = $(this).offset().left + $(this).width();
    if (e.type === 'mouseover') {
        $(this).parent().css('position', 'relative');
        $(this).parent().append(big_obj);

        big_obj.offset(function (n, c) {
            new_off = {};
            // 元素相对于顶部偏移位置 - 页面滚动过的距离 + 元素高度 大于 窗口高度
            if( $(window).height() < (c.top - $(window).scrollTop() + big_obj.height()) ){
                new_off.top = $(window).height() - big_obj.height() + $(window).scrollTop()
            } else {
                new_off.top = c.top
            }
            if (c.left <= 0) {
               new_off.left = old_offleft + 20
            } else {
                new_off.left = c.left
            }
            return new_off
        });
    } else {
        $("#big-image").remove();
    }
});

// 消息提示 默认警告
function showMessage(message, msg_type = 'bg-danger') {
    var messageJQ = $("<div class='showMessage " + msg_type + "'>" + message + "</div>");
    messageJQ.hide().appendTo("body").fadeIn(250);
    /**2秒之后自动删除生成的元素*/
    window.setTimeout(function () {
        messageJQ.fadeOut(500);
    }, 1800);
}