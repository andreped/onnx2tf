import random
random.seed(0)
import numpy as np
np.random.seed(0)
import tensorflow as tf
import onnx_graphsurgeon as gs
from utils.common_functions import convert_axis


def make_node(
    *,
    graph_node: gs.Node,
    tf_layers_dict: dict,
    **kwargs: dict,
):
    """ArgMin

    Parameters
    ----------
    graph_node: gs.Node
        graph_surgeon Node

    tf_layers_dict: dict
        optype, shape, dtype, tensorflow graph
    """
    graph_node_input: gs.Variable = graph_node.inputs[0]
    graph_node_output: gs.Variable = graph_node.outputs[0]
    shape = graph_node_output.shape
    dtype = graph_node_output.dtype

    axis = 0
    keepdims = True
    select_last_index = False

    if 'axis' in graph_node.attrs:
        axis = int(graph_node.attrs['axis'])
        # NCHW->NHWC, NCDHW->NDHWC
        axis = convert_axis(
            axis=axis,
            tensor_rank=len(shape),
        )

    if 'keepdims' in graph_node.attrs:
        # 0: False, 1: True
        keepdims = True if int(graph_node.attrs['keepdims']) == 1 else False

    if 'select_last_index' in graph_node.attrs:
        # 0: False, 1: True
        select_last_index = True if int(graph_node.attrs['select_last_index']) == 1 else False

    # Preserving Graph Structure (Dict)
    tf_layers_dict[graph_node_output.name] = {
        'optype': graph_node.op,
        'shape': shape,
        'dtype': dtype,
    }

    # Generation of TF OP
    reversed_tensor = None
    if not select_last_index:
        reversed_tensor = tf_layers_dict[graph_node_input.name]['tf_node']
    else:
        reversed_tensor = \
            tf.reverse(
                tensor=tf_layers_dict[graph_node_input.name]['tf_node'],
                axis=axis,
                name=f'{graph_node.name}_reverse',
            )

    final_tensor = None
    argmined_tensor = tf.math.argmin(
        input=reversed_tensor,
        axis=axis,
        output_type=dtype,
        name=f'{graph_node.name}_argmin',
    )
    if keepdims:
        final_tensor = \
            tf.expand_dims(
                input=argmined_tensor,
                axis=axis,
                name=f'{graph_node.name}_expand_dims',
            )
    else:
        final_tensor = argmined_tensor

    tf_layers_dict[graph_node_output.name]['tf_node'] = final_tensor