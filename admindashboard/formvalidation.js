function weightvalidate()
 {  
    error_flag = 0
    var weightname = $.trim($('#id_name').val());
    var numbers = /^[0-9]+$/;
        if (weightname  === '') {
            error_flag++
        }
        else if (!weightname.match(numbers))
        {
            error_flag++
        }

        if (error_flag === 0)
        {
            $('.errormsg').hide()
            $('#formData').submit()
        }
        else
        {
            $('.errormsg').show()
        }
}

function repsvalidate()
 {  
    error_flag = 0
    var repsname = $.trim($('#id_name').val());
    var numbers = /^[0-9]+$/;
        if (repsname  === '') {
            error_flag++
        }
        else if (!repsname.match(numbers))
        {
            error_flag++
        }

        if (error_flag === 0)
        {
            $('.errormsg').hide()
            $('#formData').submit()
        }
        else
        {
            $('.errormsg').show()
        }
}

function resttimevalidate()
 {  
    error_flag = 0
    var resttimename = $.trim($('#id_name').val());
    var numbers = /^[0-9]+$/;
        if (resttimename  === '') {
            error_flag++
        }
        else if (!resttimename.match(numbers))
        {
            error_flag++
        }

        if (error_flag === 0)
        {
            $('.errormsg').hide()
            $('#formData').submit()
        }
        else
        {
            $('.errormsg').show()
        }
}

function musclevalidate()
 {  
    error_flag = 0
    var musclename = $.trim($('#id_name').val());
    var musclename_ar = $.trim($('#id_name_ar').val());
    var char_val = /^[a-zA-Z\s]+$/;
    var numbers = /^[\u0621-\u064A\u0660-\u0669 ]+$/;
        if (musclename  == '' || musclename_ar  == '') 
        {
            $(".errormsg").show()
            if(musclename)
                {
                    $("#errormsg1").hide()
                    $('#errormsg2').html('This field is required').show()
                }
            if(musclename_ar)
                {
                    $("#errormsg2").hide()
                    $('#errormsg1').html('This field is required').show()
                }
        }
        else if (!musclename.match(char_val))
        {
            $('#errormsg1').html('Please enter alphabets only').show()
            $("#errormsg2").hide()
        }

        else if (!musclename_ar.match(numbers))
        {
            $('#errormsg2').html('Please enter alphabets only').show()
            $("#errormsg1").hide()

        }

        else
        {
            $('.errormsg').hide()
            $('.errormsg1').hide()
            $('#errormsg2').hide()
            $('#formData').submit()
        }
}

function categoryvalidate()
 {  
    error_flag = 0
    var categoryname = $.trim($('#id_name').val());
    var categoryname_ar = $.trim($('#id_name_ar').val());
    var char_val = /^[a-zA-Z\s]+$/;
    var numbers = /^[\u0621-\u064A\u0660-\u0669 ]+$/;
    if (categoryname  == '' || categoryname_ar  == '') 
    {
        $(".errormsg").show()
        if(categoryname)
            {
                $("#errormsg1").hide()
                $('#errormsg2').html('This field is required').show()
            }
        if(categoryname_ar)
            {
                $("#errormsg2").hide()
                $('#errormsg1').html('This field is required').show()
            }
    }
    else if (!categoryname.match(char_val))
    {
        $('#errormsg1').html('Please enter alphabets only').show()
        $("#errormsg2").hide()
    }

    else if (!categoryname_ar.match(numbers))
    {
        $('#errormsg2').html('Please enter alphabets only').show()
        $("#errormsg1").hide()

    }
    else
        {
            $('.errormsg').hide()
            $('.errormsg1').hide()
            $('#errormsg2').hide()
            $('#formData').submit()
        }
}

function userlevelvalidate()
 {  
    error_flag = 0
    var userlevel = $.trim($('#id_name').val());
    var userlevel_ar = $.trim($('#id_name_ar').val());
    var char_val = /^[A-Za-z\s]+$/;
    var numbers = /^[\u0621-\u064A\u0660-\u0669 ]+$/;
    if (userlevel  == '' || userlevel_ar  == '') 
    {
        $(".errormsg").show()
        if(userlevel)
            {
                $("#errormsg1").hide()
                $('#errormsg2').html('This field is required').show()

            }
        if(userlevel_ar)
            {
                $("#errormsg2").hide()
                $('#errormsg1').html('This field is required').show()
            }
    }
    else if (!userlevel.match(char_val))
    {
        $('#errormsg1').html('Please enter alphabets only').show()
        $("#errormsg2").hide()
    }

    else if (!userlevel_ar.match(numbers))
    {
        $('#errormsg2').html('Please enter alphabets only').show()
        $("#errormsg1").hide()
    }

    else
    {
        $('.errormsg').hide()
        $('#errormsg1').hide()
        $('#errormsg2').hide()
        $('#formData').submit()
    }

}

// function helpvalidate()
//  {  
//     error_flag = 0
//     var question = $.trim($('#id_question').val());
//     var question_ar = $.trim($('#id_question_ar').val());
//     var answer = CKEDITOR.instances['id_answer'].getData();
//     var answer_ar = CKEDITOR.instances['id_answer_ar'].getData();
//     var chars = /^[a-zA-Z\s]+$/;
//     var numbers = /^[\u0621-\u064A\u0660-\u0669 ]+$/;
//     if(answer == "" || answer_ar == "" || question == "" || question_ar == "")
//             {
//                 $(".errormsg").show()
//                 if(question)
//                 {
//                     $("#errormsg1").hide()
//                 }
//                 if(question_ar)
//                 {
//                     $("#errormsg3").hide()
//                 }
//                 if(answer)
//                 {
//                     $("#errormsg2").hide()
//                 }
//                 if(answer_ar)
//                 {
//                     $("#errormsg4").hide()
//                 }
//             }

//     if (answer && answer_ar && question_ar && question)
//     {
//         $('#formData').submit()
//     }
// }