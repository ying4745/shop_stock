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
function getFloat2(x){
    if (x !== '.'){
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

// 鼠标悬浮显示大图
$(".good_img").hover(function (){
    $(this).append('<p id="bigimage"><img src="' + $(this).find('img').attr('src') + '" alt="" /></p>');
    }, function () {
    $("#bigimage").remove();
});

// 消息提示 默认警告
function showMessage(message, msg_type='bg-danger') {
    var messageJQ = $("<div class='showMessage " + msg_type + "'>" + message + "</div>");
    messageJQ.hide().appendTo("body").fadeIn(250);
    /**2秒之后自动删除生成的元素*/
    window.setTimeout(function () {
        messageJQ.fadeOut(500);
    }, 1800);
}