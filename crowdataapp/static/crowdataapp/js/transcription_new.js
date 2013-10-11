$(function() {
    var FORM_SUBMITTED = gettext('<h1>Thanks for your help!</h1><button id="another">Want another file?</button>');
    $('form').on('submit', function(event) {
        event.preventDefault();
        var serializedForm = $(this).serialize();
        $.post($(this).attr('action'),
               serializedForm,
               function(data) {
                   $('#form-container').html(FORM_SUBMITTED);
               });
    });

    $(document).on('click',
                   'button#another',
                   function(data) {
                       var parts = location.pathname.split('\/');
                       location = '/' + parts[1] + '/' + parts[2] + '/another';
                   });
});
