$(function() {
    $('td.field-answers input[type=checkbox]').on('change', function(e) {
        var u = window.location;
        u += 'document_set_field_entry/' + $(this).data('field-entry') + '/';
        var checked = $(this).is(':checked');
        $.post(u,
               {
                   verified: checked,
                   csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
               },
               function(data) {
                   data.map(function(id) {
                       var c = $('td.field-answers input[data-field-entry="'+id+'"]');
                       c.prop('checked', checked);
                   });
               });
    });
});
