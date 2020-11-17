function fill_buy()
{
    var x = location.search;
    var sym = x.slice(5, -1);
    document.getElementById("symbol").value = sym;

}