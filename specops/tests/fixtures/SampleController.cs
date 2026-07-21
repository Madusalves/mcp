namespace SampleApi.Controllers;

/// <summary>
/// Expoe operacoes de consulta de pedidos.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class OrdersController : ControllerBase
{
    /// <summary>
    /// Retorna um pedido pelo identificador.
    /// </summary>
    [HttpGet("{id}")]
    public IActionResult GetById(int id)
    {
        return Ok();
    }
}
